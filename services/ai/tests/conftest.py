import os
from cryptography.fernet import Fernet as _Fernet
os.environ.setdefault("AI_KEY_ENCRYPTION_KEY", _Fernet.generate_key().decode())

import pytest
from cryptography.fernet import Fernet
from unittest.mock import AsyncMock


@pytest.fixture
def fernet():
    return Fernet.generate_key()


@pytest.fixture
def test_jwt_payload():
    return {
        "sub": "user-123",
        "email": "test@example.com",
        "workspace_ids": ["ws-1"],
        "roles": {},
    }


@pytest.fixture
def sample_message():
    return {"role": "user", "content": "Explain this code"}


@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value={
            "content": "Test response",
            "provider": "google",
            "model": "gemini-flash-1.5",
            "input_tokens": 10,
            "output_tokens": 20,
            "cost": 0.0,
            "latency_ms": 100,
        }
    )
    return client


@pytest.fixture
def mock_redis(monkeypatch):
    mock = AsyncMock()
    mock.eval = AsyncMock(return_value=[1, 1, 60])
    monkeypatch.setattr("redis.asyncio.from_url", AsyncMock(return_value=mock))
    return mock
