class AppBaseError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred"


class InsufficientQuotaError(AppBaseError):
    status_code = 402
    code = "insufficient_quota"
    message = "No usable provider keys available"

    def __init__(self, message: str | None = None, provider: str = "", model: str = ""):
        super().__init__(message or self.message)
        self.provider = provider
        self.model = model


class NoApiKeyError(AppBaseError):
    status_code = 404
    code = "no_api_key"
    message = "User has no provisioned API key"


class RateLimitExceededError(AppBaseError):
    status_code = 429
    code = "rate_limit_exceeded"
    message = "Rate limit exceeded"

    def __init__(self, message: str | None = None, provider: str = "", retry_after: float | None = None):
        super().__init__(message or self.message)
        self.provider = provider
        self.retry_after = retry_after


class ProviderUnavailableError(AppBaseError):
    status_code = 503
    code = "provider_unavailable"
    message = "LLM provider is currently unavailable"

    def __init__(self, message: str | None = None, provider: str = ""):
        super().__init__(message or self.message)
        self.provider = provider


class ProviderKeyError(AppBaseError):
    status_code = 502
    code = "provider_key_error"
    message = "Provider key provisioning failed"


class AllProvidersFailedError(AppBaseError):
    status_code = 402
    code = "all_providers_failed"
    message = "AI service is temporarily at capacity. Please try again in a few minutes."

    def __init__(self, candidates: list | None = None, message: str | None = None):
        super().__init__(message or self.message)
        self.candidates = candidates or []
        self.tried_providers = [c.get("provider", "unknown") for c in self.candidates] if self.candidates else []


class ContextOverflowError(AppBaseError):
    status_code = 413
    code = "context_overflow"
    message = "Message is too long for this model"
