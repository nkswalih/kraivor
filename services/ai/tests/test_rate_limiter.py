import pytest
from unittest.mock import AsyncMock
from app.api.dependencies.rate_limiter import LUA_SLIDING_WINDOW


pytestmark = pytest.mark.unit


class TestRateLimiter:
    async def test_lua_script_defined(self):
        assert "ZREMRANGEBYSCORE" in LUA_SLIDING_WINDOW
        assert "ZADD" in LUA_SLIDING_WINDOW
        assert "EXPIRE" in LUA_SLIDING_WINDOW

    async def test_redis_unavailable_fallbacks_gracefully(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.redis__url", None)
        from app.api.dependencies.rate_limiter import check_rate_limit

        mock_request = AsyncMock()
        mock_request.state.user_id = "test-user"
        result = await check_rate_limit(mock_request)
        assert result is None
