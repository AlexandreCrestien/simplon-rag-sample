import json
import logging
import re
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag.rag.agent.prompts import (
    ESCALATION_RESPONSE,
    EVALUATOR_PROMPT,
    GUARD_ROUTE_PROMPT,
    OUT_OF_SCOPE_RESPONSE,
    RAG_SYSTEM_PROMPT,
    RAG_USER_PROMPT,
    SYSTEM_PROMPT,
)
from rag.rag.agent.state import AgentState
from rag.config.settings import get_settings
from rag.db.models.conversation import Conversation, Message
from rag.rag.retriever import pgvector_retriever

logger = logging.getLogger(__name__)


def _extract_json(content: str) -> str:
    content = content.strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return match.group(0) if match else content


def _get_llm(settings=None, model: str = "llama3.2:1b") -> ChatOllama:
    return ChatOllama(model=model, base_url="http://host.docker.internal:11434")


async def load_history(state: AgentState, db: AsyncSession) -> dict:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == state["conversation_id"])
        .order_by(Message.created_at, Message.id)
    )
    db_messages = result.scalars().all()
    settings = get_settings()
    lc_messages: list = [
        SystemMessage(content=SYSTEM_PROMPT.format(product_name=settings.product_name))
    ]
    for msg in db_messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    lc_messages.append(HumanMessage(content=state["user_message"]))
    return {"messages": lc_messages}


async def guard_route(state: AgentState) -> dict:
    start = time.monotonic()
    settings = get_settings()
    llm = _get_llm(model="llama3.2:1b")
    prompt = GUARD_ROUTE_PROMPT.format(
        product_name=settings.product_name,
        user_message=state["user_message"],
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        data = json.loads(_extract_json(response.content))
        in_scope = bool(data.get("in_scope", True))
        needs_retrieval = bool(data.get("needs_retrieval", True))
        category = str(data.get("category", ""))
    except (json.JSONDecodeError, ValueError):
        in_scope = True
        needs_retrieval = True
        category = ""

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info("node guard_route", extra={
        "node": "guard_route",
        "in_scope": in_scope,
        "category": category,
        "latency_ms": latency_ms,
    })

    if not in_scope:
        return {
            "in_scope": False,
            "needs_retrieval": False,
            "category": "out_of_scope",
            "answer": OUT_OF_SCOPE_RESPONSE.format(product_name=settings.product_name),
            "sources": [],
        }
    return {"in_scope": True, "needs_retrieval": needs_retrieval, "category": category}


async def retrieve(state: AgentState, db: AsyncSession) -> dict:
    start = time.monotonic()
    query = state.get("rewrite_suggestion") or state["user_message"]
    chunks = await pgvector_retriever.similarity_search(query, db)
    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info("node retrieve", extra={
        "node": "retrieve",
        "chunks_count": len(chunks),
        "latency_ms": latency_ms,
    })
    return {"retrieved_chunks": chunks}


async def generate(state: AgentState) -> dict:
    start = time.monotonic()
    llm = _get_llm()
    history_msgs = state["messages"][1:-1]

    if state.get("retrieved_chunks"):
        context = "\n\n---\n\n".join(
            f"[{c['filename']} chunk {c['chunk_index']}]\n{c['content']}"
            for c in state["retrieved_chunks"]
        )
        system_content = RAG_SYSTEM_PROMPT.format(
            product_name=get_settings().product_name,
            context=context,
        )
        user_content = RAG_USER_PROMPT.format(
            question=state["user_message"],
            category=state.get("category", ""),
        )
        messages_to_send = [
            SystemMessage(content=system_content),
            *history_msgs,
            HumanMessage(content=user_content),
        ]
        sources = [c["chunk_id"] for c in state["retrieved_chunks"]]
    else:
        messages_to_send = state["messages"]
        sources = []

    response = await llm.ainvoke(messages_to_send)
    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info("node generate", extra={
        "node": "generate",
        "latency_ms": latency_ms,
    })
    return {"answer": response.content, "sources": sources}


async def evaluate(state: AgentState) -> dict:
    start = time.monotonic()
    llm = _get_llm(model="llama3.2:1b")
    context_summary = "\n".join(
        f"- [{c['filename']}]: {c['content'][:100]}..."
        for c in (state.get("retrieved_chunks") or [])
    ) or "Aucun contexte récupéré."

    prompt = EVALUATOR_PROMPT.format(
        question=state["user_message"],
        context_summary=context_summary,
        answer=state.get("answer", ""),
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        data = json.loads(_extract_json(response.content))
        score = float(data.get("score", 10))
        decision = str(data.get("decision", "answer"))
        rewrite_suggestion = str(data.get("rewrite_suggestion", ""))
    except (json.JSONDecodeError, ValueError):
        score = 10.0
        decision = "answer"
        rewrite_suggestion = ""

    retry_count = state.get("retry_count", 0) + 1
    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info("node evaluate", extra={
        "node": "evaluate",
        "score": score,
        "decision": decision,
        "retry_count": retry_count,
        "latency_ms": latency_ms,
    })
    return {
        "eval_score": score,
        "eval_decision": decision,
        "rewrite_suggestion": rewrite_suggestion,
        "retry_count": retry_count,
    }


async def escalate(state: AgentState) -> dict:
    logger.warning("node escalate — escalade vers support humain", extra={
        "node": "escalate",
    })
    settings = get_settings()
    return {
        "answer": ESCALATION_RESPONSE.format(
            product_name=settings.product_name,
            question=state["user_message"],
        ),
        "sources": [],
    }


async def save_turn(state: AgentState, db: AsyncSession) -> dict:
    user_msg = Message(
        conversation_id=state["conversation_id"],
        role="user",
        content=state["user_message"],
    )
    assistant_msg = Message(
        conversation_id=state["conversation_id"],
        role="assistant",
        content=state["answer"],
        sources=state.get("sources"),
    )
    db.add_all([user_msg, assistant_msg])
    result = await db.execute(
        select(Conversation).where(Conversation.id == state["conversation_id"])
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        from sqlalchemy import func
        conversation.metadata_ = {**conversation.metadata_, "last_updated": str(func.now())}
    await db.commit()
    return {}