"""
One-time data migration — v3.

Conversation messages always alternate: user, assistant, user, assistant...

v1 of this script sorted by (created_at, id) where random UUIDs caused
same-turn assistants to be placed before users.  v2's proximity-based
turn grouping failed because the 1 µs chaining from v1 created
continuous sequences with no natural breaks.

v3's approach: separate messages by role, interleave correctly.
For each conversation:
1. Split messages into user_msgs and assistant_msgs (each already
   correctly ordered within its own role).
2. Interleave: user[0], ass[0], user[1], ass[1], …
3. Reassign strictly increasing timestamps.
4. Backfill last_message_at.
"""

import asyncio
import sys
from datetime import timedelta

from sqlalchemy import select, text

from app.infrastructure.db.database import async_session_factory
from app.infrastructure.db.models.conversation import Conversation
from app.infrastructure.db.models.message import Message


async def fix_all():
    async with async_session_factory() as db:
        result = await db.execute(select(Conversation.id))
        conv_ids = list(result.scalars().all())
        total = len(conv_ids)
        print(f"Found {total} conversations to process")

        changed = 0
        for idx, cid in enumerate(conv_ids, 1):
            rows = await db.execute(
                select(Message).where(Message.conversation_id == cid)
            )
            msgs = list(rows.scalars().all())
            if not msgs:
                continue

            # Separate by role, keeping each group sorted by current created_at
            users = sorted(
                (m for m in msgs if m.role == "user"), key=lambda m: m.created_at
            )
            assistants = sorted(
                (m for m in msgs if m.role == "assistant"), key=lambda m: m.created_at
            )

            # Interleave: user[0], ass[0], user[1], ass[1], …
            ordered: list[Message] = []
            max_len = max(len(users), len(assistants))
            for i in range(max_len):
                if i < len(users):
                    ordered.append(users[i])
                if i < len(assistants):
                    ordered.append(assistants[i])

            base_ts = ordered[0].created_at
            for i, msg in enumerate(ordered):
                new_ts = base_ts + timedelta(microseconds=i)
                if msg.created_at != new_ts:
                    msg.created_at = new_ts
                    changed += 1

            # Backfill last_message_at
            last_ts = ordered[-1].created_at
            await db.execute(
                text(
                    "UPDATE ai.conversations SET last_message_at = :ts WHERE id = :cid"
                ).bindparams(ts=last_ts, cid=cid)
            )

            if idx % 50 == 0 or idx == total:
                print(f"  Progress: {idx}/{total}")

        await db.commit()
        print(f"\nDone! Changed {changed} message timestamps across {total} conversations.")


if __name__ == "__main__":
    print("v3 — interleaving by role (user→assistant→user→assistant…)")

    asyncio.run(fix_all())
    sys.exit(0)
