"""
apps/api_keys/views.py
 
API key management endpoints.  Views are intentionally thin.
 
POST   /api/auth/api-keys/           Create a new API key
GET    /api/auth/api-keys/           List current user's API keys
DELETE /api/auth/api-keys/<key_id>/  Revoke an API key
"""
 
from __future__ import annotations

import logging

from api_keys.selectors.api_key import get_user_api_keys
from api_keys.serializers import (
    APIKeyCreateResponseSerializer,
    APIKeyCreateSerializer,
    APIKeyListSerializer,
)
from api_keys.services.key_service import (
    APIKeyNotFoundError,
    InvalidScopeError,
    create_api_key,
    revoke_api_key,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)
 
 
class APIKeyListCreateView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        keys = get_user_api_keys(user_id=str(request.user.id))
        serializer = APIKeyListSerializer(keys, many=True)
        return Response({"api_keys": serializer.data}, status=status.HTTP_200_OK)
 
    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        try:
            created = create_api_key(
                user=request.user,
                name=serializer.validated_data["name"],
                scopes=serializer.validated_data["scopes"],
                expires_at=serializer.validated_data.get("expires_at"),
            )
        except InvalidScopeError as exc:
            return Response(
                {"error": str(exc), "error_code": "invalid_scope"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("api_key_create_failed: user_id=%s", request.user.id)
            return Response(
                {"error": "Failed to create API key.", "error_code": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
 
        # Attach raw_key transiently — serializer picks it up, DB never sees it
        created.api_key.raw_key = created.raw_key
        response_serializer = APIKeyCreateResponseSerializer(created.api_key)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
 
 
class APIKeyRevokeView(APIView):
    permission_classes = [IsAuthenticated]
 
    def delete(self, request, key_id: str):
        try:
            revoke_api_key(user=request.user, key_id=key_id)
        except APIKeyNotFoundError:
            return Response(
                {"error": "API key not found.", "error_code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception(
                "api_key_revoke_failed: user_id=%s key_id=%s", request.user.id, key_id
            )
            return Response(
                {"error": "Failed to revoke API key.", "error_code": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
 
        return Response({"message": "API key revoked successfully."}, status=status.HTTP_200_OK)