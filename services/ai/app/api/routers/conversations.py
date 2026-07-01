import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.dependencies.auth import get_current_user, JWTPayload
from app.api.dependencies.rate_limiter import check_rate_limit
from app.infrastructure.db.database import async_session_factory
from app.application.chat.conversation_repository import (
    list_conversations,
    get_messages,
    get_conversation,
)
from pydantic import BaseModel

router = APIRouter(tags=["conversations"])


class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str | None = None
    message_count: int = 0
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    model: str | None = None
    created_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    conversation_id: str
    total: int


@router.get("/conversations")
async def list_user_conversations(
    workspace_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: JWTPayload = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    async with async_session_factory() as db:
        convs = await list_conversations(
            db, user_id=user.sub, workspace_id=workspace_id, limit=limit, offset=offset
        )
        return ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=c.id,
                    title=c.title,
                    model=c.model,
                    message_count=c.message_count,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in convs
            ],
            total=len(convs),
        )


@router.get("/conversations/{conversation_id}/messages")
async def list_conversation_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: JWTPayload = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    async with async_session_factory() as db:
        conv = await get_conversation(db, conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.user_id != user.sub:
            raise HTTPException(status_code=403, detail="Access denied")

        msgs = await get_messages(db, conversation_id, limit=limit, offset=offset)
        return MessageListResponse(
            messages=[
                MessageResponse(
                    id=str(uuid.uuid4()),
                    role=m.role.value,
                    content=m.content,
                    model=m.model,
                    created_at=m.created_at,
                )
                for m in msgs
            ],
            conversation_id=conversation_id,
            total=len(msgs),
        )
