import logging
import sys

import structlog

from app.core.config import get_settings

settings = get_settings()


def bootstrap_logging() -> None:
    """Configure structured logging for the service.

    Uses structlog with JSON formatting in production and
    rich console output in development.
    """
    is_dev = settings.service.environment == "development"
    use_json = settings.logging.json_format and not is_dev

    level = getattr(logging, settings.logging.level, logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    # Suppress noisy library loggers
    for logger_name in (
        "httpx",
        "httpcore",
        "urllib3",
        "botocore",
        "aiormq",
        "asyncio",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.dev.ConsoleRenderer()
                if is_dev or not use_json
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name, typically __name__. Falls back to service name.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name or settings.otel.service_name)  # type: ignore[no-any-return]
