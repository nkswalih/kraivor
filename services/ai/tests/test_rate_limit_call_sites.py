"""Tests for enforce_rate_limit and the routes that call it.

The seed-project-docs route called check_rate_limit(user.sub, "action",
max_requests=5, window_seconds=60). check_rate_limit is a FastAPI dependency
that takes a single Request, so that call raised TypeError every time — and
the route's `except Exception` converted it into a 200 with
{"status": "error"}, so seeding silently never happened.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.dependencies.rate_limiter import enforce_rate_limit

pytestmark = pytest.mark.unit


def _mock_redis(monkeypatch, allowed=1, count=1, max_limit=5):
    redis = AsyncMock()
    redis.eval.return_value = [allowed, count, max_limit]
    monkeypatch.setattr(
        "app.api.dependencies.rate_limiter.get_redis", AsyncMock(return_value=redis)
    )
    return redis


class TestEnforceRateLimit:
    async def test_passes_budget_to_lua_script(self, monkeypatch):
        """max_requests and window_seconds must reach the script, not be dropped."""
        redis = _mock_redis(monkeypatch)
        monkeypatch.setattr("app.api.dependencies.rate_limiter.settings.redis__url", "redis://x")

        await enforce_rate_limit("user-1", "knowledge.seed", max_requests=5, window_seconds=60)

        # eval(script, num_keys, key, now, window, limit)
        args = redis.eval.call_args[0]
        assert args[1] == 1  # one Redis key
        assert args[2] == "ratelimit:ai:knowledge.seed:user-1"
        assert isinstance(args[3], float)  # now
        assert args[4] == 60  # window_seconds
        assert args[5] == 5  # max_requests

    async def test_action_is_part_of_the_key(self, monkeypatch):
        """Different actions must not share one budget."""
        redis = _mock_redis(monkeypatch)
        monkeypatch.setattr("app.api.dependencies.rate_limiter.settings.redis__url", "redis://x")

        await enforce_rate_limit("user-1", "action.a")
        await enforce_rate_limit("user-1", "action.b")

        keys = [c[0][2] for c in redis.eval.call_args_list]
        assert keys == ["ratelimit:ai:action.a:user-1", "ratelimit:ai:action.b:user-1"]

    async def test_raises_429_when_exceeded(self, monkeypatch):
        _mock_redis(monkeypatch, allowed=0, count=5, max_limit=5)
        monkeypatch.setattr("app.api.dependencies.rate_limiter.settings.redis__url", "redis://x")

        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit("user-1", "knowledge.seed", max_requests=5, window_seconds=60)

        assert exc.value.status_code == 429
        assert exc.value.detail["error"] == "rate_limit_exceeded"
        assert exc.value.detail["retry_after"] == 60

    async def test_retry_after_reflects_actual_window(self, monkeypatch):
        _mock_redis(monkeypatch, allowed=0, count=99, max_limit=99)
        monkeypatch.setattr("app.api.dependencies.rate_limiter.settings.redis__url", "redis://x")

        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit("user-1", "act", max_requests=99, window_seconds=15)

        assert exc.value.detail["retry_after"] == 15

    async def test_noop_when_redis_disabled(self, monkeypatch):
        monkeypatch.setattr("app.api.dependencies.rate_limiter.settings.redis__url", None)
        # Must not raise: with no Redis there is nothing to enforce against.
        assert await enforce_rate_limit("user-1", "act") is None

    async def test_raises_503_when_redis_errors(self, monkeypatch):
        redis = AsyncMock()
        redis.eval.side_effect = RuntimeError("connection reset")
        monkeypatch.setattr(
            "app.api.dependencies.rate_limiter.get_redis", AsyncMock(return_value=redis)
        )
        monkeypatch.setattr("app.api.dependencies.rate_limiter.settings.redis__url", "redis://x")

        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit("user-1", "act")

        assert exc.value.status_code == 503
        assert exc.value.detail["error"] == "rate_limiter_unavailable"


class TestSeedProjectDocsRoute:
    async def test_route_enforces_its_own_budget(self):
        """The route must call the callable limiter, with its own budget.

        Guards the original defect: a call with the wrong signature raised
        TypeError, which the route's except turned into a 200 + error body.
        """
        from app.api.routers import knowledge

        called = {}

        async def fake_enforce(user_id, action, *, max_requests, window_seconds):
            called.update(
                user_id=user_id,
                action=action,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )

        task = MagicMock()
        task.delay.return_value = MagicMock(id="task-123")

        with (
            patch.object(knowledge, "enforce_rate_limit", fake_enforce),
            patch.dict(
                "sys.modules",
                {"app.application.tasks.knowledge": MagicMock(seed_kraivor_project_docs=task)},
            ),
        ):
            result = await knowledge.seed_project_docs(
                workspace_id="ws-1", user=AsyncMock(sub="user-1")
            )

        assert called == {
            "user_id": "user-1",
            "action": "knowledge.seed",
            "max_requests": 5,
            "window_seconds": 60,
        }
        assert result["status"] == "queued"
        assert result["task_id"] == "task-123"

    async def test_enqueue_failure_is_not_reported_as_success(self):
        """A failed enqueue must not return 200 with status=error."""
        from app.api.routers import knowledge

        broken = MagicMock()
        broken.seed_kraivor_project_docs.delay.side_effect = RuntimeError("broker down")

        with (
            patch.object(knowledge, "enforce_rate_limit", AsyncMock()),
            patch.dict("sys.modules", {"app.application.tasks.knowledge": broken}),
            pytest.raises(HTTPException) as exc,
        ):
            await knowledge.seed_project_docs(
                workspace_id="ws-1", user=AsyncMock(sub="user-1")
            )

        assert exc.value.status_code == 503
