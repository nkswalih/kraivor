"""Tests for the outbound URL guard.

The guard is the single control behind the SSRF findings on the knowledge
engine, the multimodal ingester, and the BYOK key validator. These tests
assert that it blocks what it is supposed to block and permits what the
system legitimately fetches. A regression here re-opens SSRF, so the
blocklist is asserted explicitly rather than sampled.
"""

import pytest
import socket

from app.core.url_guard import UnsafeURLError, assert_safe_url, host_matches


class TestSchemeValidation:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/x",
            "gopher://example.com/",
            "data:text/html,<script>alert(1)</script>",
            "javascript:alert(1)",
            "//example.com/no-scheme",
            "",
        ],
    )
    def test_rejects_non_http_schemes(self, url):
        with pytest.raises(UnsafeURLError):
            assert_safe_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://api.openai.com/v1/models",
            "http://example.com/page",
            "HTTPS://EXAMPLE.COM/upper-scheme",
        ],
    )
    def test_allows_http_and_https(self, url):
        assert assert_safe_url(url) == url


class TestPrivateAddressBlocking:
    """Literal IPs need no DNS, so these are the deterministic cases."""

    @pytest.mark.parametrize(
        "url",
        [
            # Cloud metadata endpoints — the classic credential-theft target.
            "http://169.254.169.254/latest/meta-data/",
            "http://[::ffff:169.254.169.254]/latest/meta-data/",
            # Loopback.
            "http://127.0.0.1:8000/admin",
            "http://127.0.0.1/",
            "http://[::1]/",
            # RFC1918 private ranges.
            "http://10.0.0.5/internal",
            "http://172.16.4.4/internal",
            "http://192.168.1.1/",
            # Link-local and unspecified.
            "http://169.254.1.1/",
            "http://0.0.0.0/",
            # Carrier-grade NAT: not private per the stdlib, not routable.
            "http://100.64.0.1/",
        ],
    )
    def test_rejects_non_public_literals(self, url):
        with pytest.raises(UnsafeURLError):
            assert_safe_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://api.openai.com/v1",
            "https://8.8.8.8/",
            "https://[2606:4700:4700::1111]/",
        ],
    )
    def test_allows_public_literals(self, url):
        assert assert_safe_url(url) == url

    def test_self_hosted_endpoint_is_still_refused(self):
        """A private address is never legitimate here, and there is no bypass.

        Ollama or vLLM on a LAN address would be refused. That is intended:
        no supported provider is self-hosted, and an opt-out flag would be
        one careless call site away from reopening the SSRF hole.
        """
        with pytest.raises(UnsafeURLError, match="non-public address"):
            assert_safe_url("http://192.168.1.50:11434/v1")


class TestDnsResolutionBlocking:
    """Hostnames are resolved before the request; a private answer is refused."""

    def test_rejects_hostname_resolving_to_private(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", port))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(UnsafeURLError, match="non-public address"):
            assert_safe_url("https://internal.corp.example/api")

    def test_rejects_when_any_resolved_address_is_private(self, monkeypatch):
        """A split-horizon answer with one private record must still fail."""
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
            ]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(UnsafeURLError, match="non-public address"):
            assert_safe_url("https://rebind.example/api")

    def test_allows_hostname_resolving_to_public(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        assert assert_safe_url("https://example.com/api") == "https://example.com/api"

    def test_rejects_unresolvable_host(self, monkeypatch):
        def fake_getaddrinfo(host, port, *args, **kwargs):
            raise socket.gaierror("Name or service not known")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(UnsafeURLError, match="Cannot resolve host"):
            assert_safe_url("https://nonexistent.invalid/api")

    def test_rejects_malformed_url(self):
        with pytest.raises(UnsafeURLError):
            assert_safe_url("https://[not-an-ipv6]/path")


class TestHostMatches:
    """Substring host checks are how a token leak reached github.com.evil.com."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/nkswalih/kraivor",
            "https://www.github.com/nkswalih/kraivor",
            "https://api.github.com/repos/x",
            "https://GITHUB.COM/case-insensitive",
            "https://github.com./trailing-dot",
        ],
    )
    def test_matches_apex_and_subdomains(self, url):
        assert host_matches(url, "github.com") is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com.evil.com/attacker/repo.git",
            "https://evil.com/?ref=github.com",
            "https://notgithub.com/x",
            "https://githubXcom/x",
            "https://evil.com/github.com",
        ],
    )
    def test_rejects_lookalike_and_embedded_hosts(self, url):
        assert host_matches(url, "github.com") is False

    def test_matches_any_of_several_domains(self):
        assert host_matches("https://arxiv.org/abs/1234", "github.com", "arxiv.org")

    def test_returns_false_for_missing_host(self):
        assert host_matches("not-a-url", "github.com") is False
        assert host_matches("", "github.com") is False
