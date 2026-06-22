"""
authentication/oauth/base.py

Shared interfaces and base classes for all OAuth providers.
Reused by GitHub and Google implementations.
"""

from __future__ import annotations

from dataclasses import dataclass

from abc import ABC, abstractmethod


@dataclass(frozen=True)
class OAuthUserInfo:
    """Normalised user identity returned by any OAuth provider."""

    provider: str
    provider_user_id: str  # stable unique ID (GitHub id / Google sub)
    email: str
    name: str
    avatar_url: str | None
    email_verified: bool
    raw: dict  # original payload for audit / raw_data column


class OAuthStateService(ABC):
    """Contract for CSRF state token generation and validation."""

    @abstractmethod
    def generate(self) -> str: ...

    @abstractmethod
    def validate(self, state: str) -> bool: ...

    @abstractmethod
    def consume(self, state: str) -> bool:
        """Validate AND delete in one atomic operation."""
        ...


class OAuthTokenExchanger(ABC):
    """Contract for authorization-code → token exchange."""

    @abstractmethod
    def exchange(self, code: str) -> dict: ...


class OAuthIdentityVerifier(ABC):
    """Contract for verifying provider-issued identity tokens."""

    @abstractmethod
    def verify(self, raw_token_response: dict) -> OAuthUserInfo: ...
