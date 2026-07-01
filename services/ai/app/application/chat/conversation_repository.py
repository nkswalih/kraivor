import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.models.conversation import Conversation
from app.infrastructure.db.models.message import Message
from app.domain.entities.conversation import Conversation as ConversationEntity
from app.domain.entities.message import Message as MessageEntity, MessageRole


async def ensure_conversation(
    db: AsyncSession,
    conversation_id: str,
    user_id: str,
    workspace_id: str,
    model: str | None = None,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(
            id=conversation_id,
            user_id=user_id,
            workspace_id=workspace_id,
            title="New conversation",
            model=model,
            message_count=0,
        )
        db.add(conv)
        await db.flush()
    return conv


async def save_message(db: AsyncSession, msg: MessageEntity) -> Message:
    row = Message(
        id=str(uuid.uuid4()),
        conversation_id=msg.conversation_id,
        user_id=msg.user_id or "",
        role=msg.role.value,
        content=msg.content,
        model=msg.model,
        tokens_input=msg.tokens_input,
        tokens_output=msg.tokens_output,
        msg_metadata=msg.metadata,
    )
    db.add(row)
    await db.flush()
    return row


async def update_conversation_after_message(
    db: AsyncSession,
    conversation_id: str,
    title: str | None = None,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return

    conv.message_count = (conv.message_count or 0) + 2
    conv.last_message_at = datetime.now(timezone.utc)

    if title:
        first_msg_result = await db.execute(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.role == "user",
            ).order_by(Message.created_at.asc()).limit(1)
        )
        first_msg = first_msg_result.scalar_one_or_none()
        if first_msg:
            content = first_msg.content
            conv.title = content[:80] + ("..." if len(content) > 80 else "")
        else:
            conv.title = title[:80]

    if model:
        conv.model = model
    await db.flush()


async def list_conversations(
    db: AsyncSession,
    user_id: str,
    workspace_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ConversationEntity]:
    query = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.last_message_at))
        .offset(offset)
        .limit(limit)
    )
    if workspace_id:
        query = query.where(Conversation.workspace_id == workspace_id)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        ConversationEntity(
            id=str(r.id),
            user_id=r.user_id,
            workspace_id=r.workspace_id,
            title=r.title,
            model=r.model,
            message_count=r.message_count,
            is_archived=r.is_archived,
            created_at=r.created_at,
            updated_at=r.updated_at or r.created_at,
        )
        for r in rows
    ]


async def get_messages(
    db: AsyncSession,
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[MessageEntity]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        MessageEntity(
            role=MessageRole(r.role),
            content=r.content,
            conversation_id=str(r.conversation_id),
            user_id=r.user_id,
            model=r.model,
            tokens_input=r.tokens_input,
            tokens_output=r.tokens_output,
            metadata=r.msg_metadata,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def get_conversation(
    db: AsyncSession,
    conversation_id: str,
) -> ConversationEntity | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        return None
    return ConversationEntity(
        id=str(r.id),
        user_id=r.user_id,
        workspace_id=r.workspace_id,
        title=r.title,
        model=r.model,
        message_count=r.message_count,
        is_archived=r.is_archived,
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
    )
