from datetime import UTC, datetime

from app.infrastructure.db.models.usage_log import UsageLog


class UsageTracker:
    async def log_usage(
        self,
        db_session,
        user_id: str,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        agent_name: str | None = None,
        status: str = "success",
    ) -> None:
        log = UsageLog(
            user_id=user_id,
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            agent_name=agent_name,
            status=status,
            logged_at=datetime.now(UTC),
        )
        db_session.add(log)

    async def check_budget(
        self,
        db_session,
        user_id: str,
        monthly_limit: int = 1_000_000,
    ) -> bool:
        from sqlalchemy import func, select

        result = await db_session.execute(
            select(func.sum(UsageLog.tokens_input + UsageLog.tokens_output))
            .where(
                UsageLog.user_id == user_id,
                UsageLog.logged_at >= datetime.now(UTC).replace(day=1),
            )
        )
        total = result.scalar() or 0
        return total < monthly_limit
