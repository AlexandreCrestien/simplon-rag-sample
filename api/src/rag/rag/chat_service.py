import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag.db.models.conversation import Conversation, Message
from rag.rag.agent.graph import build_graph


class ConversationNotFoundError(Exception):
    pass


@dataclass
class ConversationResult:
    conversation_id: uuid.UUID


@dataclass
class MessageResult:
    message_id: uuid.UUID | None
    role: str
    content: str
    sources: list[str]


@dataclass
class MessageItem:
    message_id: uuid.UUID
    role: str
    content: str
    sources: list[str] | None
    created_at: datetime


class ChatService:
    async def create_conversation(self, db: AsyncSession) -> ConversationResult:
        conversation = Conversation()
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return ConversationResult(conversation_id=conversation.id)

    async def send_message(
        self, conversation_id: uuid.UUID, content: str, db: AsyncSession
    ) -> MessageResult:
        result = await db.execute(
            select(Conversation).where(Conversation.id == str(conversation_id))
        )
        if result.scalar_one_or_none() is None:
            raise ConversationNotFoundError(conversation_id)

        # --- LOG DÉBUT D'INVOCATION ---
        logging.info("Starting agent invocation", extra={
            "conversation_id": str(conversation_id)
        })
        start_time = time.time()

        graph = build_graph(db)
        final_state = await graph.ainvoke(
            {
                "conversation_id": str(conversation_id),
                "user_message": content,
                "messages": [],
                "retrieved_chunks": [],
                "answer": "",
                "sources": [],
                "needs_retrieval": False,
                "in_scope": True,
                "category": "",
                "eval_score": None,
                "eval_decision": "",
                "rewrite_suggestion": "",
                "retry_count": 0,
            },
        )

        # --- LOG FIN D'INVOCATION + LATENCE TOTALE ---
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logging.info("Agent invocation complete", extra={
            "conversation_id": str(conversation_id),
            "total_latency_ms": duration_ms,
            "retry_count": final_state.get("retry_count", 0)
        })

        msg_result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == str(conversation_id),
                Message.role == "assistant",
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        assistant_msg = msg_result.scalar_one_or_none()

        return MessageResult(
            message_id=assistant_msg.id if assistant_msg else None,
            role="assistant",
            content=final_state["answer"],
            sources=final_state.get("sources", []),
        )

    async def list_messages(
        self, conversation_id: uuid.UUID, db: AsyncSession
    ) -> list[MessageItem]:
        result = await db.execute(
            select(Conversation).where(Conversation.id == str(conversation_id))
        )
        if result.scalar_one_or_none() is None:
            raise ConversationNotFoundError(conversation_id)

        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == str(conversation_id))
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        return [
            MessageItem(
                message_id=m.id,
                role=m.role,
                content=m.content,
                sources=m.sources,
                created_at=m.created_at,
            )
            for m in messages
        ]
