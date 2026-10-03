def log_safe(value: object) -> str:
    """Escape CR and LF so caller-supplied text cannot forge a log record.

    Handlers write the formatted message verbatim, so a CR or LF inside a
    value the caller controls -- a room id, a message id, a webhook payload
    field -- terminates the line early and lets the rest of the value be read
    as a separate, attacker-authored log entry. That is enough to plant
    convincing records or to hide a real one.

    The value is escaped rather than stripped so operators keep the evidence
    of what was actually sent.

    The trailing ``replace`` on LF is load-bearing rather than stylistic.
    CodeQL's ``py/log-injection`` query recognises exactly one sanitizer
    shape in Python: a ``.replace()`` whose first argument is a literal
    CRLF or LF. The chain has to end with that call or the finding returns.
    Escaping CR first is harmless and keeps the output readable.

    Note this returns ``str``, so it must not wrap an argument that a format
    string renders with a numeric specifier -- ``%d`` against a ``str``
    raises ``TypeError`` when the record is formatted. An int cannot contain
    a newline, so those call sites do not need wrapping in the first place.
    """
    return str(value).replace("\r", "\\r").replace("\n", "\\n")
