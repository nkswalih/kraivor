"""
apps/api_keys/permissions/scopes.py

Scope-based permission class for API key authentication.

Usage:
    class AnalysisView(APIView):
        permission_classes = [IsAuthenticated, HasScope("analysis:read")]

Rules:
  - JWT-authenticated callers (request.auth is not an APIKey) pass freely —
    scopes are a machine-auth concept only.
  - "admin" scope on an API key bypasses all other scope checks.
  - All other API key callers must carry the specific required scope.
"""

from __future__ import annotations

from api_keys.models import APIKey
from rest_framework.permissions import BasePermission


class HasScope(BasePermission):
    """Checks that request.auth (an APIKey) carries the required scope."""

    def __init__(self, scope: str) -> None:
        self.required_scope = scope

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        # JWT auth — request.auth is a token payload dict, not an APIKey
        if not isinstance(request.auth, APIKey):
            return True

        api_key: APIKey = request.auth

        # "admin" is a superscope — bypasses all other checks
        if "admin" in api_key.scopes:
            return True

        return self.required_scope in api_key.scopes
