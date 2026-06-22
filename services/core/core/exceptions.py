import logging
import traceback
from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
)
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class AppException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An unexpected error occurred."
    default_code = "internal_error"

    def __init__(self, detail=None, code=None, extra=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.extra = extra or {}
        super().__init__(detail, code)


class ResourceNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "not_found"


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict."
    default_code = "conflict"


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Validation failed."
    default_code = "validation_error"


class RateLimitError(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests. Please try again later."
    default_code = "rate_limited"


class ServiceUnavailableError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"


ERROR_TYPE_MAP = {
    "not_found": "about:blank",
    "permission_denied": "about:blank",
    "validation_error": "about:blank",
    "conflict": "about:blank",
    "rate_limited": "about:blank",
    "internal_error": "about:blank",
    "service_unavailable": "about:blank",
}


def _build_rfc_7807(
    detail: str, code: str, status_code: int, extra: dict | None = None
) -> dict:
    return {
        "type": ERROR_TYPE_MAP.get(code, "about:blank"),
        "title": code.replace("_", " ").title(),
        "status": status_code,
        "detail": detail,
        "code": code,
        **(extra or {}),
    }


def core_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is not None:
        detail = response.data
        if isinstance(detail, dict):
            flat_detail = "; ".join(
                f"{k}: {', '.join(v) if isinstance(v, list) else v}"
                for k, v in detail.items()
            )
        elif isinstance(detail, list):
            flat_detail = "; ".join(str(d) for d in detail)
        else:
            flat_detail = str(detail)

        code = getattr(exc, "default_code", "error")
        status_code = response.status_code

        response.data = _build_rfc_7807(
            detail=flat_detail or str(exc),
            code=code,
            status_code=status_code,
        )
        return response

    if isinstance(exc, DjangoValidationError):
        return JsonResponse(
            _build_rfc_7807(detail=str(exc), code="validation_error", status_code=422),
            status=422,
        )

    if isinstance(exc, DjangoPermissionDenied):
        return JsonResponse(
            _build_rfc_7807(detail=str(exc), code="permission_denied", status_code=403),
            status=403,
        )

    if isinstance(exc, ObjectDoesNotExist):
        return JsonResponse(
            _build_rfc_7807(detail=str(exc), code="not_found", status_code=404),
            status=404,
        )

    logger.error(
        "exception.unhandled",
        extra={
            "error": str(exc),
            "traceback": "".join(traceback.format_tb(exc.__traceback__))
            if exc.__traceback__
            else None,
        },
    )

    if settings.DEBUG:
        raise exc

    return JsonResponse(
        _build_rfc_7807(
            detail="An unexpected error occurred.",
            code="internal_error",
            status_code=500,
        ),
        status=500,
    )
