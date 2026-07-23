import pytest
from unittest.mock import AsyncMock

from app.api.routers.chat import chat_service

pytestmark = pytest.mark.unit


class TestChatRouter:
    async def test_models_endpoint(self):
        from app.api.routers.chat import list_models

        mock_user = AsyncMock()
        mock_user.sub = "test-user"
        result = await list_models(user=mock_user)

        assert "models" in result
        assert "default" in result
        assert len(result["models"]) >= 3

    async def test_chat_non_streaming(self, monkeypatch):
        from app.api.routers.chat import chat

        monkeypatch.setattr(
            chat_service,
            "chat",
            AsyncMock(
                return_value={
                    "response": "Test answer",
                    "usage": {"model": "test", "input_tokens": 5, "output_tokens": 10},
                    "sources": [],
                }
            ),
        )

        mock_request = AsyncMock()
        mock_request.workspace_id = "ws-1"
        mock_request.message = "hello"
        mock_request.conversation_id = None
        mock_request.repo_ids = None
        mock_request.stream = False
        mock_request.mode = "normal"
        mock_request.model = None

        mock_user = AsyncMock()
        mock_user.sub = "test-user"

        mock_req = AsyncMock()
        mock_req.headers = {}

        result = await chat(request=mock_request, user=mock_user, req=mock_req, _=None)

        assert result.content == "Test answer"
        assert result.conversation_id is not None
