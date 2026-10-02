"""Guard outbound URLs against server-side request forgery.

Every code path in this service that fetches a caller-supplied URL routes
through :func:`assert_safe_url` first. Without it, a user can point the
knowledge engine, the web-fetch tools, or the multimodal ingester at
internal infrastructure (the cloud metadata endpoint, the Postgres or
Redis container, the cluster's own control plane) and read the response.

Two checks are applied, in this order:

1. Syntax — the URL must be absolute, and its scheme must be http or https.
   This rejects ``file:``, ``gopher:``, ``ftp:`` and friends.
2. Reachability — the resolved host must not point at loopback, link-local,
   private, or otherwise reserved address space.

The second check resolves DNS *before* the request is made, so a hostname
that maps to a private address is rejected rather than fetched. That closes
the common case. It does not close DNS rebinding, where an attacker
controls a name that resolves to a public address during the check and a
private one when the socket connects. Closing that requires pinning the
resolved address and connecting to it directly, which this module does not
do — see the accepted-risks section in ``DEPLOYMENT.md``.

Neither check survives a redirect. A public host that answers ``302`` with
``Location: http://169.254.169.254/`` puts the very next request on
infrastructure the caller was just refused. Callers must therefore run with
redirect following disabled and route each ``Location`` through
:func:`resolve_redirect`, which re-applies both checks to every hop.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Statuses that carry a Location header worth following. 303 switches the
# method to GET, which is already what these callers issue, so it needs no
# special handling here.
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

MAX_REDIRECT_HOPS = 5


def host_matches(url: str, *domains: str) -> bool:
    """Return True if the URL's hostname is one of ``domains`` or a subdomain.

    Use this instead of ``"github.com" in url``. Substring checks match at
    any position, so ``https://github.com.evil.com/x`` and
    ``https://evil.com/?ref=github.com`` both pass a substring test while
    the actual host is attacker-controlled.

    Args:
        url: The URL to inspect.
        *domains: Apex domains to match, e.g. ``"github.com"``.

    Returns:
        True if the host is ``domains`` or ends with ``.`` + a domain.
    """
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return False
    if not host:
        return False
    host = host.lower().rstrip(".")
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in domains)


class UnsafeURLError(ValueError):
    """Raised when a URL is malformed or points at a non-public address."""


def _is_blocked_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if this address is not a routable public address."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        return True
    if ip.is_multicast or ip.is_unspecified:
        return True
    # 100.64.0.0/10 — carrier-grade NAT. Not private per the stdlib, but
    # it is not reachable from the public internet either.
    if ip.version == 4 and ip in ipaddress.ip_network("100.64.0.0/10"):
        return True
    # IPv4-mapped IPv6 (::ffff:169.254.169.254) resolves to an IPv4
    # address that the v6 checks above do not inspect.
    mapped = getattr(ip, "ipv4_mapped", None)
    return mapped is not None and _is_blocked_address(mapped)


def _resolve_addresses(host: str, port: int) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve ``host`` to every address it currently maps to."""
    try:
        # AF_UNSPEC so both A and AAAA records come back.
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host: {host}") from exc

    addresses = []
    for info in infos:
        sockaddr = info[4]
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    if not addresses:
        raise UnsafeURLError(f"Cannot resolve host: {host}")
    return addresses


def assert_safe_url(url: str) -> str:
    """Validate ``url`` for safe outbound fetching.

    There is deliberately no bypass flag. Every supported LLM provider is a
    public SaaS endpoint, so a private or loopback destination is never
    legitimate here, and an opt-out would be one careless call away from
    re-opening the hole. If a self-hosted provider is ever added, that
    decision belongs in this function with its own explicit allowlist, not
    in a boolean at a call site.

    Args:
        url: The absolute URL to check.

    Returns:
        The URL, unchanged.

    Raises:
        UnsafeURLError: If the scheme is not http/https, or the host
            resolves to loopback, link-local, private, or reserved space.
    """
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL must be a non-empty string")

    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise UnsafeURLError(f"Malformed URL: {exc}") from exc

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError(
            f"URL scheme not allowed: {parts.scheme or '(none)'}. "
            f"Only http and https are permitted."
        )

    host = parts.hostname
    if not host:
        raise UnsafeURLError("URL is missing a hostname")

    port = parts.port or (443 if parts.scheme.lower() == "https" else 80)

    # A literal IP in the URL can be checked without DNS.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _is_blocked_address(literal):
            raise UnsafeURLError(f"URL points at a non-public address: {host}")
        return url

    for address in _resolve_addresses(host, port):
        if _is_blocked_address(address):
            raise UnsafeURLError(
                f"Host {host} resolves to a non-public address ({address})"
            )

    return url


def resolve_redirect(current_url: str, location: str | None) -> str:
    """Resolve a ``Location`` header against ``current_url`` and re-validate it.

    Validating only the *initial* URL does not make a redirecting fetch
    safe. A public host can answer ``302`` with a ``Location`` pointing at
    ``169.254.169.254``, and a client that follows redirects will fetch it,
    so the guard is consulted and then bypassed in the same request. Every
    hop has to be checked, which is why no outbound client in this service
    is allowed to follow redirects on its own.

    Args:
        current_url: The URL that produced the redirect.
        location: The raw ``Location`` header value, which may be relative.

    Returns:
        The absolute, validated target URL.

    Raises:
        UnsafeURLError: If the resolved target is not safe to fetch.
    """
    if not location or not location.strip():
        raise UnsafeURLError("Redirect response carried no Location header")
    target = urljoin(current_url, location.strip())
    assert_safe_url(target)
    return target
