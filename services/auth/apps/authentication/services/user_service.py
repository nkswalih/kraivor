"""
OAuth User Service
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from django.contrib.auth import get_user_model

from ..models import OAuthIdentity

logger = logging.getLogger(__name__)
User = get_user_model()


def find_or_create_oauth_user(provider: str, oauth_id: str, email: str, name: Optional[str], avatar_url: Optional[str]) -> tuple:
    identity = OAuthIdentity.objects.filter(provider=provider, provider_user_id=oauth_id).exclude(deleted_at__isnull=False).select_related("user").first()

    if identity:
        identity.user.email = email
        identity.user.name = name or identity.user.name
        if avatar_url:
            identity.user.avatar_url = avatar_url
        identity.user.save()
        return identity.user, False

    user = User.objects.filter(email=email).first()
    created = False

    if not user:
        user = User.objects.create_user(email=email, name=name or "", avatar_url=avatar_url or "")
        created = True

    OAuthIdentity.objects.create(user=user, provider=provider, provider_user_id=oauth_id, provider_email=email)

    return user, created


def find_oauth_user(provider: str, oauth_id: str) -> Optional[object]:
    identity = OAuthIdentity.objects.filter(provider=provider, provider_user_id=oauth_id).exclude(deleted_at__isnull=False).select_related("user").first()
    return identity.user if identity else None