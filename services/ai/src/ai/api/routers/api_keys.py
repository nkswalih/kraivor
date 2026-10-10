from typing import Annotated

import base64
import os
import uuid
from cryptography.fernet import Fernet
from datetime import UTC, datetime
from fastapi import APIRouter, Depends

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.schemas.api_key import (
    CreateKeyRequest,
    KeyResponse,
    ProvisionRequest,
    ProvisionResponse,
)
from app.application.provisioning.key_provisioning import KeyProvisioner
from app.core.config import settings

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]

router = APIRouter(tags=["api_keys"])

_key = settings.key_encryption_key or base64.urlsafe_b64encode(os.urandom(32)).decode()
encrypter = Fernet(_key.encode() if isinstance(_key, str) else _key)
provisioner = KeyProvisioner(encrypter=encrypter)


@router.post("/api-keys", response_model=KeyResponse)
async def create_api_key(request: CreateKeyRequest, user: CurrentUser):
    return KeyResponse(
        id=str(uuid.uuid4()),
        key=f"sk-{uuid.uuid4().hex}",
        prefix=request.name[:8],
        scopes=request.scopes or ["chat:basic"],
        rate_limit_rpm=request.rate_limit_rpm or 60,
        created_at=datetime.now(UTC),
    )


@router.post("/api-keys/provision", response_model=ProvisionResponse)
async def provision_provider_key(request: ProvisionRequest, user: CurrentUser):
    result = await provisioner.provision_openrouter_key(
        user_id=user.sub, user_email=user.email, tier=request.tier or "free"
    )
    return ProvisionResponse(
        provider=request.provider,
        model_access=result.get("models", []),
        rate_limit=result.get("rate_limits", {}),
        provisioned_at=datetime.now(UTC).isoformat(),
    )
