"""Fuzz target for the SSRF guard.

`assert_safe_url` is the only thing standing between a caller-supplied URL and
an outbound request, and it is a parser: it splits a string, reads a port, and
classifies addresses. Parsers are exactly where the interesting bugs live, and
the existing tests are hand-written examples rather than a search.

The target asserts properties rather than examples, so it keeps working after
someone adds a case nobody thought of:

  I1  `assert_safe_url` either returns its input unchanged or raises exactly
      `UnsafeURLError`. Anything else escaping -- a bare ValueError from
      `.port`, an AttributeError, a RecursionError -- breaks the contract every
      caller relies on. In `ingester.ingest_url` the only handler is
      `except UnsafeURLError`, so anything else becomes a 500 instead of a
      clean rejection: attacker-chosen input controlling the response status.
      This invariant found exactly that: `http://host:99999/` and
      `http://host:-1/` both raised ValueError before the fix.

  I2  Accepting a URL twice yields the same answer. A guard whose verdict
      depends on call ordering is a guard that can be talked out of its answer.

  I3  A URL is never accepted on one call and rejected on the next.

  I4  If an accepted URL's host parses as an IP literal, that address must not
      be one `_is_blocked_address` rejects. This is the disagreement that
      matters: the split parser and the address classifier are separate pieces
      of code, and IPv4-mapped IPv6 exists precisely because they can drift.

DNS is stubbed. Every non-literal host resolves to one fixed public address,
which keeps the target hermetic and fast -- a real lookup per input would make
libFuzzer spend its budget on the network instead of on the parser.

Run locally without atheris (available on any platform):

    python fuzzing/fuzz_url_guard.py --iterations 20000

Under libFuzzer, which needs atheris and therefore a Linux runner:

    python fuzzing/fuzz_url_guard.py corpus/url_guard
"""

from __future__ import annotations

import ipaddress
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services", "ai"))

from app.core import url_guard  # noqa: E402
from app.core.url_guard import UnsafeURLError, _is_blocked_address, assert_safe_url  # noqa: E402

# A routable public address. Anything that is not a literal IP lands here,
# so the guard's verdict for those hosts is "accept", deterministically.
PUBLIC_IP = "93.184.216.34"

AF_INET = 2
SOCK_STREAM = 1
IPPROTO_TCP = 6


def _stub_getaddrinfo(host, port, *args, **kwargs):
    return [
        (AF_INET, SOCK_STREAM, IPPROTO_TCP, "", (PUBLIC_IP, int(port or 0))),
    ]


url_guard.socket.getaddrinfo = _stub_getaddrinfo


def check(data: bytes) -> None:
    """Assert I1-I4 for one input. Raises AssertionError on any violation."""
    # surrogateescape so every byte sequence becomes a usable str; a fuzz target
    # that cannot represent its own input is not testing anything.
    url = data.decode("utf-8", errors="surrogateescape")

    try:
        accepted = assert_safe_url(url)
    except UnsafeURLError:
        return  # rejection is a complete, correct outcome
    except Exception as exc:  # noqa: BLE001 - the point is to name the type
        raise AssertionError(
            f"I1: assert_safe_url raised {type(exc).__name__} instead of "
            f"UnsafeURLError for {url!r}: {exc}"
        ) from exc

    if not isinstance(accepted, str):
        raise AssertionError(f"I1: returned {type(accepted).__name__}, not str")

    # I2: same input, same answer, same value.
    try:
        again = assert_safe_url(accepted)
    except UnsafeURLError as exc:
        raise AssertionError(
            f"I2: {url!r} was accepted, then rejected on re-check: {exc}"
        ) from exc
    if again != accepted:
        raise AssertionError(
            f"I2: re-check of {url!r} returned {again!r}, not {accepted!r}"
        )

    # I4: an accepted literal-IP host must not be a blocked address.
    try:
        host = url_guard.urlsplit(url).hostname
    except ValueError:
        host = None
    if host:
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None and _is_blocked_address(literal):
            raise AssertionError(
                f"I4: {url!r} was accepted but host {host} is blocked by "
                f"_is_blocked_address"
            )


# atheris calls this. Named to match the convention OSS-Fuzz and Scorecard look
# for when they decide whether a project actually fuzzes anything.
def TestOneInput(data: bytes) -> None:  # noqa: N802
    check(data)


# ── local driver ──────────────────────────────────────────────────────────
# Kept so the target is runnable by contributors and in tests, not only in CI.
# Coverage-guided fuzzing still needs atheris; this just proves the
# invariants hold over a corpus and a pile of mutations, which is the part
# that catches regressions when the harness itself is edited.

SEEDS = [
    b"http://example.com/",
    b"https://example.com/path?q=1#frag",
    b"http://127.0.0.1/",
    b"http://169.254.169.254/latest/meta-data/",
    b"http://[::1]/",
    b"http://[::ffff:169.254.169.254]/",
    b"http://10.0.0.1/",
    b"http://100.64.0.1/",
    b"http://0.0.0.0/",
    b"http://[::]/",
    b"http://224.0.0.1/",
    b"http://example.com:99999/",  # I1 regression: bare ValueError
    b"http://example.com:-1/",  # I1 regression: bare ValueError
    b"http://example.com:0/",
    b"http://example.com:65535/",
    b"http://example.com:65536/",
    b"http://user:pass@example.com/",
    b"http://example.com\\@127.0.0.1/",
    b"http://example.com\r\nHost: evil",
    b"http://exa mple.com/",
    b"http://[::1/",
    b"http://:80/",
    b"http:///path",
    b"HTTP://EXAMPLE.COM/",
    b"file:///etc/passwd",
    b"gopher://example.com/",
    b"",
    b"http://xn--e1afmkfd.xn--p1ai/",
    b"http://example.com./",
]

MUTATORS = [
    lambda r, b: bytes(r.randrange(256) for _ in range(r.randrange(0, 40))),
    lambda r, b: b[: r.randrange(0, len(b) + 1)],
    lambda r, b: b + bytes(r.randrange(256) for _ in range(r.randrange(1, 8))),
    lambda r, b: b.replace(b"127.0.0.1", b"0.0.0.0"),
    lambda r, b: b.replace(b":", b"::"),
    lambda r, b: b.replace(b"example.com", b"127.0.0.1"),
    lambda r, b: b + b":" + str(r.randrange(-5, 70000)).encode(),
    lambda r, b: b.replace(b"http", b"htTp"),
    lambda r, b: b + b"\x00" * r.randrange(1, 4),
]


def _load_corpus() -> list[bytes]:
    corpus = list(SEEDS)
    corpus_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "corpus", "url_guard")
    if os.path.isdir(corpus_dir):
        for name in sorted(os.listdir(corpus_dir)):
            path = os.path.join(corpus_dir, name)
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    corpus.append(fh.read())
    return corpus


def drive(iterations: int, seed: int) -> int:
    rng = random.Random(seed)
    corpus = _load_corpus()
    failures = 0

    for _ in range(iterations):
        data = rng.choice(corpus)
        for _ in range(rng.randrange(0, 4)):
            data = rng.choice(MUTATORS)(rng, data)
        try:
            check(data)
        except AssertionError as exc:
            failures += 1
            print(f"\n  FAIL on input {data!r}\n    {exc}")
            if failures >= 5:
                break

    print(
        f"\n{iterations} inputs over {len(corpus)} seeds, rng seed {seed}: "
        f"{failures} violation(s)"
    )
    return failures


def main() -> int:
    if "--iterations" in sys.argv:
        iterations = int(sys.argv[sys.argv.index("--iterations") + 1])
        seed = 20261003
        if "--rng-seed" in sys.argv:
            seed = int(sys.argv[sys.argv.index("--rng-seed") + 1])
        return 1 if drive(iterations, seed) else 0

    try:
        import atheris  # noqa: PLC0415
    except ImportError:
        print(
            "atheris is not installed (it ships native libFuzzer binaries and "
            "only runs on Linux).\n"
            "Falling back to the local driver. For coverage-guided fuzzing:\n"
            "    pip install atheris && python fuzzing/fuzz_url_guard.py corpus/url_guard",
            file=sys.stderr,
        )
        return 1 if drive(5000, 20261003) else 0

    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
    return 0


if __name__ == "__main__":
    sys.exit(main())