import httpx
import logging
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.constants import TIER_BUDGET_LIMITS, TIER_MODEL_ACCESS, TIER_RATE_LIMITS

logger = logging.getLogger(__name__)


class KeyProvisioner:
    def __init__(self, encrypter: Fernet):
        self.encrypter = encrypter

    async def provision_openrouter_key(
        self, user_id: str, user_email: str, tier: str = "free"
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/keys",
                headers={
                    "Authorization": f"Bearer {settings.openrouter__master__key}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": f"kraivor-{user_id[:8]}",
                    "models": self._get_model_access(tier),
                    "max_budget": self._get_budget_limit(tier),
                    "rate_limit": self._get_rate_limit(tier),
                },
            )
            response.raise_for_status()
            data = response.json()

        encrypted = self.encrypter.encrypt(data["key"].encode())

        return {
            "encrypted_key": encrypted.decode(),
            "provider_key_id": data["id"],
            "rate_limit": self._get_rate_limit(tier),
            "model_access": self._get_model_access(tier),
        }

    async def rotate_provider_key(
        self, user_id: str, current_provider: str
    ) -> tuple[str, str]:
        rotation_chain = ["openrouter", "groq", "google"]
        current_idx = rotation_chain.index(current_provider)
        next_idx = (current_idx + 1) % len(rotation_chain)
        next_provider = rotation_chain[next_idx]

        logger.info(
            "rotating_provider",
            user_id=user_id,
            from_provider=current_provider,
            to_provider=next_provider,
        )

        if next_provider == "openrouter":
            result = await self.provision_openrouter_key(user_id, "")
        elif next_provider == "groq":
            result = await self._provision_from_pool("groq")
        else:
            result = await self._provision_from_pool("google")

        return next_provider, result["encrypted_key"]

    async def _provision_from_pool(self, provider: str) -> dict:
        return {
            "encrypted_key": self.encrypter.encrypt(provider.encode()).decode(),
            "provider_key_id": f"pool-{provider}",
            "rate_limit": {"requests": 30, "interval": "1m"},
            "model_access": ["*"],
        }

    def _get_model_access(self, tier: str) -> list[str]:
        return TIER_MODEL_ACCESS.get(tier, TIER_MODEL_ACCESS["free"])

    def _get_budget_limit(self, tier: str) -> float:
        return TIER_BUDGET_LIMITS.get(tier, TIER_BUDGET_LIMITS["free"])

    def _get_rate_limit(self, tier: str) -> dict:
        return TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["free"])
