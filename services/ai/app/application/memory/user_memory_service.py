import re

import logging
import uuid
from datetime import UTC, datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.user_fact import UserFact
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)

USER_CONTEXT_CACHE_TTL = 300  # 5 minutes

# Patterns to extract user facts from messages
_NAME_PATTERNS = [
    re.compile(
        r"(?:my name is|call me )([A-Za-z][A-Za-z\s\-']{1,30}?)(?:[,\.!]|\s+and|\s*$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:you can call me |name's )([A-Za-z][A-Za-z\s\-']{1,30}?)(?:[,\.!]|\s*$)",
        re.IGNORECASE,
    ),
]

# Words that indicate the capture is NOT a name (conversational filler / verbs)
_NAME_REJECTION = frozenset({
    "currently", "working", "trying", "using", "learning", "building",
    "developing", "testing", "setting", "installing", "configuring",
    "running", "debugging", "fixing", "starting", "beginning", "looking",
    "want", "need", "like", "prefer", "think", "know", "believe",
    "going", "doing", "making", "creating", "writing", "reading",
    "the", "a", "an", "some", "more", "new", "old", "good", "bad",
    "this", "that", "it", "all", "my", "your", "our", "their",
})

_PREFERENCE_PATTERNS = [
    re.compile(
        r"(?:I\s+(?:prefer|like|use|work with|enjoy|love)\s+)([\w\s+#]+?)(?:[,\.!]|for|because|when|\s*$)",
        re.IGNORECASE,
    )
]

_TECH_STACK_PATTERNS = [
    re.compile(
        r"(?:stack is|tech stack|using|working with|primarily use|mostly use)\s+([A-Za-z0-9#+.\s,]+?)(?:[,\.!]|for|because|\s*$)",
        re.IGNORECASE,
    )
]


async def extract_and_store_facts(
    db: AsyncSession, user_id: str, message: str, conversation_id: str | None
) -> list[UserFact]:
    facts: list[UserFact] = []

    for pattern in _NAME_PATTERNS:
        match = pattern.search(message)
        if match:
            name = match.group(1).strip().title()
            # Reject if too short, too long, or contains filler words
            words = name.lower().split()
            if (
                len(name) < 3
                or len(name) > 30
                or any(w in _NAME_REJECTION for w in words)
            ):
                continue
            facts.append(
                UserFact(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    fact_type="identity",
                    fact_key="name",
                    fact_value=name,
                    confidence=0.6,
                    source_conversation_id=conversation_id,
                )
            )
            break

    for pattern in _PREFERENCE_PATTERNS:
        for match in pattern.finditer(message):
            pref = match.group(1).strip()
            if 2 < len(pref) < 200:
                key = f"preference_{pref.lower().replace(' ', '_')[:50]}"
                facts.append(
                    UserFact(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        fact_type="preference",
                        fact_key=key,
                        fact_value=pref,
                        confidence=0.7,
                        source_conversation_id=conversation_id,
                    )
                )

    for pattern in _TECH_STACK_PATTERNS:
        match = pattern.search(message)
        if match:
            stack = match.group(1).strip()
            if len(stack) > 2:
                facts.append(
                    UserFact(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        fact_type="tech_stack",
                        fact_key="tech_stack",
                        fact_value=stack,
                        confidence=0.7,
                        source_conversation_id=conversation_id,
                    )
                )

    saved = []
    for fact in facts:
        try:
            # Upsert: check if fact already exists
            existing = await db.execute(
                select(UserFact).where(
                    UserFact.user_id == user_id,
                    UserFact.fact_key == fact.fact_key,
                    UserFact.fact_type == fact.fact_type,
                    UserFact.deleted_at.is_(None),
                )
            )
            existing_row = existing.scalar_one_or_none()
            if existing_row:
                existing_row.fact_value = fact.fact_value
                existing_row.confidence = max(existing_row.confidence, fact.confidence)
                existing_row.source_conversation_id = conversation_id
            else:
                db.add(fact)
                saved.append(fact)
        except Exception as e:
            logger.warning("Failed to store fact %s: %s", fact.fact_key, e)

    if saved:
        await db.flush()

    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = await get_redis()
        await r.delete(f"userctx:{user_id}")
    except Exception:
        pass

    return saved


async def get_user_context(db: AsyncSession, user_id: str, limit: int = 20) -> str:
    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = await get_redis()
        cached = await r.get(f"userctx:{user_id}")
        if cached is not None:
            return cached
    except Exception:
        pass

    result = await db.execute(
        select(UserFact)
        .where(UserFact.user_id == user_id, UserFact.deleted_at.is_(None))
        .order_by(UserFact.confidence.desc(), UserFact.updated_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    if not rows:
        return ""

    parts = []
    for row in rows:
        parts.append(f"- {row.fact_type}: {row.fact_value}")

    context_str = "\n".join(parts)

    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = await get_redis()
        await r.setex(f"userctx:{user_id}", USER_CONTEXT_CACHE_TTL, context_str)
    except Exception:
        pass

    return context_str


async def clear_user_facts(
    db: AsyncSession, user_id: str, fact_type: str | None = None
) -> None:
    stmt = (
        update(UserFact)
        .where(UserFact.user_id == user_id, UserFact.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
    )
    if fact_type:
        stmt = stmt.where(UserFact.fact_type == fact_type)
    await db.execute(stmt)
    await db.flush()


async def store_fact_explicit(
    user_id: str, fact_type: str, fact_key: str, fact_value: str
) -> str:
    """Store a fact explicitly via the AI tool (no regex extraction needed)."""
    async with async_session_factory() as db:
        try:
            existing = await db.execute(
                select(UserFact).where(
                    UserFact.user_id == user_id,
                    UserFact.fact_key == fact_key,
                    UserFact.fact_type == fact_type,
                    UserFact.deleted_at.is_(None),
                )
            )
            existing_row = existing.scalar_one_or_none()
            if existing_row:
                existing_row.fact_value = fact_value
                existing_row.confidence = 1.0
            else:
                fact = UserFact(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    fact_type=fact_type,
                    fact_key=fact_key,
                    fact_value=fact_value,
                    confidence=1.0,
                )
                db.add(fact)
            await db.commit()
            try:
                from app.infrastructure.cache.redis_client import get_redis
                r = await get_redis()
                await r.delete(f"userctx:{user_id}")
            except Exception:
                pass
            return f"Remembered: {fact_type} → {fact_key} = {fact_value}"
        except Exception as e:
            await db.rollback()
            logger.warning("Failed to store explicit fact: %s", e)
            return f"Failed to store fact: {e}"
