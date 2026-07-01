import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet
from app.application.provisioning.key_provisioning import KeyProvisioner


pytestmark = pytest.mark.unit


class TestKeyProvisioning:
    async def test_provision_openrouter_key(self, fernet):
        encrypter = Fernet(fernet)
        provisioner = KeyProvisioner(encrypter=encrypter)

        with patch("app.application.provisioning.key_provisioning.httpx.AsyncClient") as mock:
            mock.return_value.__aenter__.return_value.post = AsyncMock()
            mock.return_value.__aenter__.return_value.post.return_value.json = MagicMock(
                return_value={"id": "key-1", "key": "sk-test"}
            )
            mock.return_value.__aenter__.return_value.post.return_value.raise_for_status = MagicMock()

            result = await provisioner.provision_openrouter_key("user-1", "test@test.com", "free")

        assert "encrypted_key" in result
        assert result["provider_key_id"] == "key-1"

    async def test_rotate_provider(self, fernet):
        encrypter = Fernet(fernet)
        provisioner = KeyProvisioner(encrypter=encrypter)

        with patch.object(provisioner, "provision_openrouter_key", AsyncMock(
            return_value={"encrypted_key": "test", "provider_key_id": "k-1"}
        )):
            provider, key = await provisioner.rotate_provider_key("user-1", "groq")

        assert provider == "google"
