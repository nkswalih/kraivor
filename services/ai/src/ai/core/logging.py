import logging
import structlog


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)


def log_safe(value: object) -> str:
    """Escape CR and LF so caller-supplied text cannot forge a log record.

    Handlers write the formatted message verbatim, so a CR or LF inside a
    value the caller controls -- a workspace slug, an uploaded filename, a
    webhook payload field -- terminates the line early and lets the rest of
    the value be read as a separate, attacker-authored log entry. That is
    enough to plant convincing records or to hide a real one.

    The value is escaped rather than stripped so operators keep the evidence
    of what was actually sent.

    The trailing ``replace`` on LF is load-bearing rather than stylistic.
    CodeQL's ``py/log-injection`` query recognises exactly one sanitizer
    shape in Python: a ``.replace()`` whose first argument is a literal
    CRLF or LF. The chain has to end with that call or the finding returns.
    Escaping CR first is harmless and keeps the output readable.
    """
    return str(value).replace("\r", "\\r").replace("\n", "\\n")
