"""Integration tests for ChatService — tests the LangGraph pipeline directly,
without going through the HTTP layer."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag.db.models.conversation import Conversation, Message
from rag.rag.chat_service import ChatService, ConversationNotFoundError


# ── helpers ────────────────────────────────────────────────────────────────────


def _llm(content: str) -> MagicMock:
    """Fake ChatMistralAI whose ainvoke returns `content`."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content=content))
    return mock


_GUARD_OUT_OF_SCOPE = json.dumps({"in_scope": False, "needs_retrieval": False, "category": "out_of_scope"})
_GUARD_NO_RETRIEVAL = json.dumps({"in_scope": True, "needs_retrieval": False, "category": "general"})
_GUARD_WITH_RETRIEVAL = json.dumps({"in_scope": True, "needs_retrieval": True, "category": "support"})
_EVAL_ANSWER = json.dumps({"score": 9.0, "decision": "answer", "rewrite_suggestion": ""})
_EVAL_REWRITE = json.dumps({"score": 5.0, "decision": "rewrite", "rewrite_suggestion": "reformulated query"})
_LLM_ANSWER = "This is a mocked answer."
_CHUNKS = [{"chunk_id": "chunk-1", "filename": "doc.pdf", "chunk_index": 0, "content": "Relevant content."}]


async def _create_conversation(db: AsyncSession) -> uuid.UUID:
    conv = Conversation()
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv.id


# ── fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def service() -> ChatService:
    return ChatService()


# ── tests ──────────────────────────────────────────────────────────────────────


async def test_send_message_unknown_conversation_raises(service: ChatService, db_session: AsyncSession):
    with pytest.raises(ConversationNotFoundError):
        await service.send_message(uuid.uuid4(), "Hello", db_session)


async def test_out_of_scope_saves_refusal_and_no_sources(service: ChatService, db_session: AsyncSession):
    """guard_route returns in_scope=False → pipeline short-circuits to save_turn."""
    conv_id = await _create_conversation(db_session)

    with patch("rag.rag.agent.nodes._get_llm", side_effect=[_llm(_GUARD_OUT_OF_SCOPE)]):
        result = await service.send_message(conv_id, "Tell me a joke", db_session)

    assert result.role == "assistant"
    assert result.sources == []

    msgs = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == str(conv_id))
            .order_by(Message.created_at)
        )
    ).scalars().all()
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "Tell me a joke"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == result.content


async def test_direct_answer_no_retrieval(service: ChatService, db_session: AsyncSession):
    """guard_route returns needs_retrieval=False → generate without retrieval."""
    conv_id = await _create_conversation(db_session)

    llm_calls = [_llm(_GUARD_NO_RETRIEVAL), _llm(_LLM_ANSWER), _llm(_EVAL_ANSWER)]
    with patch("rag.rag.agent.nodes._get_llm", side_effect=llm_calls):
        result = await service.send_message(conv_id, "What is the weather?", db_session)

    assert result.content == _LLM_ANSWER
    assert result.sources == []

    msgs = (
        await db_session.execute(
            select(Message).where(Message.conversation_id == str(conv_id))
        )
    ).scalars().all()
    assert len(msgs) == 2


async def test_rag_answer_with_sources(service: ChatService, db_session: AsyncSession):
    """guard_route returns needs_retrieval=True → retrieve → generate → evaluate(answer)."""
    conv_id = await _create_conversation(db_session)

    llm_calls = [_llm(_GUARD_WITH_RETRIEVAL), _llm(_LLM_ANSWER), _llm(_EVAL_ANSWER)]
    with patch("rag.rag.agent.nodes._get_llm", side_effect=llm_calls), \
         patch("rag.rag.retriever.pgvector_retriever.similarity_search", new=AsyncMock(return_value=_CHUNKS)):
        result = await service.send_message(conv_id, "What are the refund conditions?", db_session)

    assert result.content == _LLM_ANSWER
    assert result.sources == ["chunk-1"]


async def test_rewrite_once_then_answer(service: ChatService, db_session: AsyncSession):
    """evaluate returns rewrite once, then answer. Needs agent_max_retries=3 to avoid
    forced escalation on the second evaluate call."""
    conv_id = await _create_conversation(db_session)

    llm_calls = [
        _llm(_GUARD_WITH_RETRIEVAL),
        _llm(_LLM_ANSWER),    # generate 1
        _llm(_EVAL_REWRITE),  # evaluate 1 → rewrite (retry_count=1 < 3)
        _llm(_LLM_ANSWER),    # generate 2
        _llm(_EVAL_ANSWER),   # evaluate 2 → answer (retry_count=2 < 3)
    ]
    similarity_mock = AsyncMock(return_value=_CHUNKS)
    settings_mock = MagicMock(agent_max_retries=3, product_name="Simplon")

    with patch("rag.rag.agent.nodes._get_llm", side_effect=llm_calls), \
         patch("rag.rag.retriever.pgvector_retriever.similarity_search", new=similarity_mock), \
         patch("rag.rag.agent.graph.get_settings", return_value=settings_mock):
        result = await service.send_message(conv_id, "My question", db_session)

    assert result.content == _LLM_ANSWER
    assert similarity_mock.call_count == 2


async def test_escalation_after_max_retries(service: ChatService, db_session: AsyncSession):
    """After agent_max_retries=2 evaluations, _eval_decision forces escalation."""
    conv_id = await _create_conversation(db_session)

    llm_calls = [
        _llm(_GUARD_WITH_RETRIEVAL),
        _llm(_LLM_ANSWER),    # generate 1
        _llm(_EVAL_REWRITE),  # evaluate 1 → rewrite (retry_count=1 < 2)
        _llm(_LLM_ANSWER),    # generate 2
        _llm(_EVAL_REWRITE),  # evaluate 2 → _eval_decision forces escalate (retry_count=2 >= 2)
    ]
    with patch("rag.rag.agent.nodes._get_llm", side_effect=llm_calls), \
         patch("rag.rag.retriever.pgvector_retriever.similarity_search", new=AsyncMock(return_value=_CHUNKS)):
        result = await service.send_message(conv_id, "Problematic question", db_session)

    assert result.sources == []
    # The escalate node sets a fixed escalation message — verify it's non-empty
    assert result.content
    assert result.role == "assistant"
