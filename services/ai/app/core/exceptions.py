class AppBaseError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred"


class InsufficientQuotaError(AppBaseError):
    status_code = 429
    code = "insufficient_quota"
    message = "No usable provider keys available"


class NoApiKeyError(AppBaseError):
    status_code = 404
    code = "no_api_key"
    message = "User has no provisioned API key"


class RateLimitExceededError(AppBaseError):
    status_code = 429
    code = "rate_limit_exceeded"
    message = "Rate limit exceeded"


class ProviderUnavailableError(AppBaseError):
    status_code = 503
    code = "provider_unavailable"
    message = "LLM provider is currently unavailable"


class ProviderKeyError(AppBaseError):
    status_code = 502
    code = "provider_key_error"
    message = "Provider key provisioning failed"
