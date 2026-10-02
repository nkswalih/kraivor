"""`get_client_ip` must not pass request-header text through unchecked.

`X-Forwarded-For` is attacker-controlled. It was previously trusted
verbatim after `.strip()`, which is not sufficient:

  * `strip()` only trims the ends, so an embedded CR/LF survived;
  * a value containing `:` survived, and the result is interpolated into
    the Redis keys `LoginLockoutManager` counts failed attempts against;
  * an arbitrary string reached audit log lines that auth's `verbose`
    formatter renders verbatim.

These cover the extraction rules directly. The log-injection call sites are
covered in `test_log_injection_sanitisation.py`.
"""

from types import SimpleNamespace

import pytest
from authentication.security import get_client_ip

# A CR/LF injection payload: the rendered log line must not split. The
# second line is shaped exactly like a real record - level, timestamp,
# module - so a log parser cannot tell it apart from a genuine entry.
FORGERY = "10.0.0.1\r\nINFO 2026-01-01 00:00:00 authentication.views forged_entry"


def _request(**meta: str) -> SimpleNamespace:
    return SimpleNamespace(META=meta)


class TestXForwardedForIsTrustedOnlyWhenItIsAnIP:
    def test_a_plain_ipv4_is_used(self) -> None:
        request = _request(HTTP_X_FORWARDED_FOR="203.0.113.7", REMOTE_ADDR="10.1.1.1")
        assert get_client_ip(request) == "203.0.113.7"

    def test_a_plain_ipv6_is_used(self) -> None:
        request = _request(HTTP_X_FORWARDED_FOR="2001:db8::1", REMOTE_ADDR="10.1.1.1")
        assert get_client_ip(request) == "2001:db8::1"

    def test_the_first_hop_wins(self) -> None:
        request = _request(
            HTTP_X_FORWARDED_FOR="203.0.113.7, 70.41.3.18, 150.172.238.178",
            REMOTE_ADDR="10.1.1.1",
        )
        assert get_client_ip(request) == "203.0.113.7"

    def test_surrounding_whitespace_is_tolerated(self) -> None:
        request = _request(
            HTTP_X_FORWARDED_FOR="  203.0.113.7  , 70.41.3.18", REMOTE_ADDR="10.1.1.1"
        )
        assert get_client_ip(request) == "203.0.113.7"

    def test_addresses_are_normalised(self) -> None:
        """`2001:db8::0001` and `2001:db8::1` are the same client.

        Returning the caller's spelling would let one client present as
        many distinct lockout buckets.
        """
        long_form = get_client_ip(_request(HTTP_X_FORWARDED_FOR="2001:0db8:0000::0001"))
        short_form = get_client_ip(_request(HTTP_X_FORWARDED_FOR="2001:db8::1"))
        assert long_form == short_form == "2001:db8::1"


class TestUntrustedHeaderValuesAreRejected:
    @pytest.mark.parametrize(
        ("label", "value"),
        [
            ("crlf_injection", FORGERY),
            ("key_separator", "1.2.3.4:6379"),
            ("arbitrary_text", "not-an-ip"),
            ("empty", "   "),
            ("sql-ish", "' OR 1=1 --"),
            ("newline_only", "\n"),
            ("partial_ip", "203.0.113"),
            ("trailing_dot", "203.0.113.7."),
        ],
    )
    def test_a_bad_forwarded_for_falls_back_to_remote_addr(
        self, label: str, value: str
    ) -> None:
        request = _request(HTTP_X_FORWARDED_FOR=value, REMOTE_ADDR="198.51.100.9")
        result = get_client_ip(request)
        assert result == "198.51.100.9", f"{label}: {value!r}"

    def test_a_bad_forwarded_for_cannot_forge_a_log_line(self) -> None:
        request = _request(HTTP_X_FORWARDED_FOR=FORGERY, REMOTE_ADDR="198.51.100.9")
        result = get_client_ip(request)
        assert "\n" not in result
        assert "\r" not in result

    def test_the_result_never_contains_the_key_separator(self) -> None:
        """The value is spliced into `login_attempts:{email}:{ip}`."""
        for value in ("1.2.3.4:6379", FORGERY, "nope"):
            request = _request(HTTP_X_FORWARDED_FOR=value, REMOTE_ADDR="198.51.100.9")
            assert ":" not in get_client_ip(request)


class TestFallbacks:
    def test_remote_addr_is_used_when_the_header_is_absent(self) -> None:
        assert get_client_ip(_request(REMOTE_ADDR="198.51.100.9")) == "198.51.100.9"

    def test_remote_addr_ipv6_is_used(self) -> None:
        assert get_client_ip(_request(REMOTE_ADDR="2001:db8::2")) == "2001:db8::2"

    def test_a_missing_remote_addr_falls_back_to_loopback(self) -> None:
        assert get_client_ip(_request()) == "127.0.0.1"

    def test_an_unparseable_remote_addr_does_not_raise(self) -> None:
        """A Unix-socket deployment puts a filesystem path in REMOTE_ADDR."""
        assert get_client_ip(_request(REMOTE_ADDR="/run/app.sock")) == "127.0.0.1"

    def test_no_header_and_no_remote_addr(self) -> None:
        assert get_client_ip(SimpleNamespace(META={})) == "127.0.0.1"


class TestLockoutKeyShape:
    """The IP lands directly in a Redis key, so it must stay key-safe."""

    def test_a_valid_ip_produces_exactly_three_key_segments(self) -> None:
        ip = get_client_ip(_request(HTTP_X_FORWARDED_FOR="203.0.113.7"))
        assert f"login_attempts:someone@example.com:{ip}".count(":") == 2

    def test_a_hostile_header_cannot_add_key_segments(self) -> None:
        ip = get_client_ip(
            _request(HTTP_X_FORWARDED_FOR="1.2.3.4:victim@example.com:1.2.3.4")
        )
        key = f"login_attempts:someone@example.com:{ip}"
        assert key.count(":") == 2
