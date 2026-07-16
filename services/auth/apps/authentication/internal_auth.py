"""
Internal request authentication helper.

Validates X-Internal-Request header against a shared secret token
using constant-time comparison to prevent timing attacks.
"""

import hmac
from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status


def verify_internal_request(request: Request) -> bool:
    """Return True if the request carries a valid internal secret."""
    header_name = getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request")
    secret = getattr(settings, "INTERNAL_REQUEST_TOKEN", "")
    header_value = request.headers.get(header_name)
    if not header_value or not secret:
        return False
    return hmac.compare_digest(header_value.encode(), secret.encode())


def require_internal_request(request: Request) -> Response | None:
    """Return a 403 Response if the internal header is invalid, else None."""
    if verify_internal_request(request):
        return None
    return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
