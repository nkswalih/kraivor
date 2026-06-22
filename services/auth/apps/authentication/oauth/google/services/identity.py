"""
authentication/oauth/google/services/identity.py

Creates or retrieves the Kraivor User + OAuthIdentity for a verified
Google user.

Pattern:
  1. Look up OAuthIdentity by (provider="google", provider_user_id=sub)
  2. If found → return linked user (existing login)
  3. If not found → look up user by email
     a. If user exists → link Google identity to existing account
     b. If not → create new User + OAuthIdentity

Token storage:
  - Google access token encrypted with Fernet before DB write
  - Google refresh token encrypted with Fernet before DB write
  - Raw claims stored in raw_data for audit
"""

from __future__ import annotations

import logging
from datetime import timedelta

from authentication.models import OAuthIdentity
from authentication.oauth.base import OAuthUserInfo
from authentication.oauth.encryption import encrypt_token
from django.db import transaction
from django.utils import timezone
from users.models import User

logger = logging.getLogger(__name__)


class GoogleIdentityService:
    """
    Handles the User ↔ OAuthIdentity lifecycle for Google OAuth.

    All DB writes are wrapped in a transaction to prevent partial state
    if something fails mid-way.
    """

    @transaction.atomic
    def get_or_create(
        self,
        user_info: OAuthUserInfo,
        raw_token_response: dict,
    ) -> tuple[User, bool]:
        """
        Find or create a User and their Google OAuthIdentity.

        Args:
            user_info: Verified identity from GoogleIDTokenVerifier.
            raw_token_response: Original token response from Google
                                 (for storing encrypted tokens).

        Returns:
            (user, created) — created=True when a brand-new User was made.
        """
        # ── 1. Try to find existing OAuth identity ──────────────────────────
        try:
            identity = OAuthIdentity.objects.select_related("user").get(
                provider="google",
                provider_user_id=user_info.provider_user_id,
                deleted_at__isnull=True,
            )
            user = identity.user
            self._update_identity_tokens(identity, raw_token_response, user_info)
            logger.info(
                "google_oauth_existing_user: user_id=%s email=%s",
                user.id,
                user_info.email,
            )
            return user, False

        except OAuthIdentity.DoesNotExist:
            pass

        # ── 2. Try to find existing user by email ────────────────────────────
        created = False
        try:
            user = User.objects.get(email__iexact=user_info.email, is_active=True)

            if user_info.avatar_url:
                user.avatar_url = user_info.avatar_url
                user.save(update_fields=["avatar_url"])
                
            logger.info(
                "google_oauth_link_existing_account: user_id=%s email=%s",
                user.id,
                user_info.email,
            )
        except User.DoesNotExist:
            # ── 3. Create new user ───────────────────────────────────────────
            user = User.objects.create(
                email=user_info.email,
                name=user_info.name or user_info.email.split("@")[0],
                avatar_url=user_info.avatar_url,
                email_verified=True,  # Verified by Google
                is_active=True,
                # No password — OAuth-only users cannot sign in with password
                password="",
            )
            created = True
            logger.info(
                "google_oauth_new_user_created: user_id=%s email=%s",
                user.id,
                user_info.email,
            )

        # ── 4. Create OAuthIdentity record ───────────────────────────────────
        expires_at = None
        expires_in = raw_token_response.get("expires_in")
        if expires_in:
            expires_at = timezone.now() + timedelta(seconds=int(expires_in))

        access_token = raw_token_response.get("access_token")
        refresh_token = raw_token_response.get("refresh_token")

        OAuthIdentity.objects.create(
            user=user,
            provider="google",
            provider_user_id=user_info.provider_user_id,
            provider_email=user_info.email,
            access_token_encrypted=encrypt_token(access_token) if access_token else "",
            refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else "",
            expires_at=expires_at,
            raw_data={
                "sub": user_info.provider_user_id,
                "email": user_info.email,
                "name": user_info.name,
                "picture": user_info.avatar_url,
                "email_verified": user_info.email_verified,
            },
        )

        return user, created

    def _update_identity_tokens(
        self,
        identity: OAuthIdentity,
        raw_token_response: dict,
        user_info: OAuthUserInfo,
    ) -> None:
        """Refresh stored tokens on every login (tokens rotate)."""
        update_fields = ["access_token_encrypted", "updated_at"]

        access_token = raw_token_response.get("access_token")

        if access_token:
            identity.access_token_encrypted = encrypt_token(access_token)

        # Google only returns refresh_token on first grant; preserve existing if absent
        new_refresh = raw_token_response.get("refresh_token")
        if new_refresh:
            identity.refresh_token_encrypted = encrypt_token(new_refresh)
            update_fields.append("refresh_token_encrypted")

        expires_in = raw_token_response.get("expires_in")
        if expires_in:
            identity.expires_at = timezone.now() + timedelta(seconds=int(expires_in))
            update_fields.append("expires_at")

        identity.save(update_fields=update_fields)
