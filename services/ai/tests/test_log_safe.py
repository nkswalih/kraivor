"""log_safe() is the barrier CodeQL recognises for py/log-injection.

Two things are pinned here, and the second is the one that actually matters:

* the escaping behaviour, which is what stops a forged log record;
* the *shape* of the escape chain.

CodeQL's Python log-injection query defines exactly one sanitizer -- a
``.replace()`` whose first argument is a literal CRLF or LF -- and uses that
call node as a taint barrier. Reorder the chain or drop the LF replace and the
barrier is gone. Both changes are accepted by every behavioural test here,
yet all ~50 call sites using this helper report ``py/log-injection`` again on
the next scan. The behavioural tests cannot catch that. This one can, which is
why it is written against the source rather than the return value.
"""

import inspect
import re

from app.core.logging import log_safe

# A CR/LF payload whose second line is shaped exactly like a real record -
# level, timestamp, module - which is what a log parser cannot tell apart
# from a genuine entry.
FORGERY = "ws-1\r\nINFO 2026-01-01 00:00:00 knowledge_engine forged_entry"


class TestEscaping:
    def test_carriage_return_is_escaped(self):
        assert log_safe("a\rb") == "a\\rb"

    def test_line_feed_is_escaped(self):
        assert log_safe("a\nb") == "a\\nb"

    def test_crlf_becomes_two_escapes(self):
        assert log_safe("a\r\nb") == "a\\r\\nb"

    def test_no_raw_line_break_survives(self):
        """The property that matters: it cannot open a second record."""
        escaped = log_safe(FORGERY)
        assert "\n" not in escaped
        assert "\r" not in escaped

    def test_the_payload_is_kept_rather_than_discarded(self):
        """Stripping would hide the attempt; escaping keeps it diagnosable."""
        assert "forged_entry" in log_safe(FORGERY)

    def test_an_ordinary_value_is_unchanged(self):
        assert log_safe("access_denied") == "access_denied"

    def test_non_strings_are_stringified(self):
        assert log_safe(7) == "7"
        assert log_safe(None) == "None"


class TestCodeQLBarrierShape:
    def test_the_chain_ends_with_the_lf_replace(self):
        source = inspect.getsource(log_safe)
        first_args = re.findall(r"\.replace\(\s*([^,]+?),", source)

        assert first_args, f"no .replace() call found in:\n{source}"
        assert first_args[-1].strip() == '"\\n"', (
            "the final .replace() must take a literal LF as its first argument; "
            "that exact call is the only py/log-injection barrier CodeQL "
            f"recognises in Python. Found {first_args[-1]!r} instead, so every "
            "call site using this helper would report again."
        )

    def test_the_helper_returns_str(self):
        """It must never wrap a %d argument -- that raises TypeError."""
        assert isinstance(log_safe(1), str)
        assert isinstance(log_safe("x"), str)
