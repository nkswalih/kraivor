import uuid
import base64
import os
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends
from app.api.dependencies.auth import get_current_user, JWTPayload
from app.api.schemas.api_key import CreateKeyRequest, KeyResponse, ProvisionRequest, ProvisionResponse
from app.application.provisioning.key_provisioning import KeyProvisioner
from app.core.config import settings

router = APIRouter(tags=["api_keys"])

_key = settings.key_encryption_key or base64.urlsafe_b64encode(os.urandom(32)).decode()
encrypter = Fernet(_key.encode() if isinstance(_key, str) else _key)
provisioner = KeyProvisioner(encrypter=encrypter)


@router.post("/api-keys", response_model=KeyResponse)
async def create_api_key(
    request: CreateKeyRequest,
    user: JWTPayload = Depends(get_current_user),
):
    return KeyResponse(
        id=str(uuid.uuid4()),
        key=f"sk-{uuid.uuid4().hex}",
        prefix=request.name[:8],
        scopes=request.scopes or ["chat:basic"],
        rate_limit_rpm=request.rate_limit_rpm or 60,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/api-keys/provision", response_model=ProvisionResponse)
async def provision_provider_key(
    request: ProvisionRequest,
    user: JWTPayload = Depends(get_current_user),
):
    result = await provisioner.provision_openrouter_key(
        user_id=user.sub,
        user_email=user.email,
        tier=request.tier or "free",
    )
    return ProvisionResponse(
        provider=request.provider,
        model_access=result.get("models", []),
        rate_limit=result.get("rate_limits", {}),
        provisioned_at=datetime.now(timezone.utc).isoformat(),
    )
