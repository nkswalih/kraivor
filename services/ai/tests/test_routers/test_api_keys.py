import pytest

from app.api.schemas.api_key import CreateKeyRequest, ProvisionRequest

pytestmark = pytest.mark.unit


class TestApiKeysRouter:
    async def test_create_key_schema(self):
        req = CreateKeyRequest(name="test-key", scopes=["chat:basic"])
        assert req.name == "test-key"

    async def test_provision_request_schema(self):
        req = ProvisionRequest(provider="openrouter", tier="free")
        assert req.provider == "openrouter"
