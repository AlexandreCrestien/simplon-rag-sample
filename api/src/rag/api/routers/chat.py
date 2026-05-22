import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag.db.session import get_db
from rag.rag.chat_service import ChatService, ConversationNotFoundError

router = APIRouter(prefix="/conversations", tags=["chat"])


class MessageRequest(BaseModel):
    content: str


@router.post("")
async def create_conversation(db: AsyncSession = Depends(get_db)) -> dict:
    # LOG : On note la création sans PII
    logging.info("Creating new conversation")

    result = await ChatService().create_conversation(db)

    # On peut loguer l'ID généré pour le suivi
    logging.info("Conversation created", extra={"conversation_id": str(result.conversation_id)})
    
    return {"conversation_id": str(result.conversation_id)}


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # IMPORTANT : On logue l'intention, mais SURTOUT PAS body.content (PII)
    logging.info("Processing new user message", extra={"conversation_id": str(conversation_id)})

    try:
        result = await ChatService().send_message(conversation_id, body.content, db)
    except ConversationNotFoundError:
        # LOG : WARNING car c'est une erreur client (404)
        logging.warning("Message failed: Conversation not found", extra={"conversation_id": str(conversation_id)})
        raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        # LOG : Niveau ERROR pour les exceptions imprévues
        logging.error(f"Unexpected error in send_message: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return {
        "message_id": str(result.message_id) if result.message_id else None,
        "role": result.role,
        "content": result.content,
        "sources": result.sources,
    }


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    try:
        items = await ChatService().list_messages(conversation_id, db)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return [
        {
            "message_id": str(item.message_id),
            "role": item.role,
            "content": item.content,
            "sources": item.sources,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]
