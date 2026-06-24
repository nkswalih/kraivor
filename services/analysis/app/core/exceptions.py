from typing import Any


class AppBaseError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "internal_error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class NotFoundError(AppBaseError):
    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "not_found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=404, details=details)


class ValidationError(AppBaseError):
    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "validation_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, code=code, status_code=422, details=details
        )


class ConfigurationError(AppBaseError):
    def __init__(
        self,
        message: str = "Service configuration error",
        code: str = "configuration_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, code=code, status_code=500, details=details
        )


class ConflictError(AppBaseError):
    def __init__(
        self,
        message: str = "Resource conflict",
        code: str = "conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=409, details=details)


class ServiceUnavailableError(AppBaseError):
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        code: str = "service_unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, code=code, status_code=503, details=details
        )
