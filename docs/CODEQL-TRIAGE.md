# CodeQL triage record

This file records how the open CodeQL alerts were triaged: what was a real
defect and was fixed, and what was reviewed and dismissed with a reason.
Dismissals here are documented rather than blanket-suppressed, so a future
review can disagree with a specific call instead of re-triaging from zero.

Alert counts are as of 2026-10-02: **341 open** — 267 CodeQL + 74 Scorecard
checks — plus **1 open Dependabot** and **0 open secret-scanning**.

Those are the counts CodeQL reported for `dev`, i.e. the *baseline*. Two
things move the number afterwards, and they are different in kind:

- **Fixes do not close an alert.** An alert stays open until CodeQL re-scans
  a branch containing the fix, so every count below is "before".
- **Dismissals do.** 217 reviewed dismissals were filed from
  `security/codeql-triage-r3`, which leaves 124 open. Of the 69
  `PinnedDependenciesID` alerts, the 16 on Dockerfile `FROM` lines were
  deliberately *not* dismissed; see *Not dismissed: Docker `FROM` pins*.

The 267 CodeQL findings span 14 rules. The list is dominated by lint-class
rules with no security impact:

| Count | Rule | Class |
| ---: | --- | --- |
| 97 | `py/unused-global-variable` | lint |
| 62 | `py/log-injection` | security |
| 34 | `py/ineffectual-statement` | lint |
| 24 | `py/stack-trace-exposure` | security |
| 15 | `py/unused-import` | lint |
| 10 | `py/import-and-import-from` | lint |
| 7 | `py/unnecessary-lambda` | lint |
| 5 | `py/undefined-export` | correctness |
| 3 each | `py/empty-except`, `py/mixed-returns`, `py/partial-ssrf` | mixed |
| 2 | `py/call/wrong-arguments` | mixed |
| 1 each | `py/full-ssrf`, `py/weak-sensitive-data-hashing` | mixed |

Thirteen further rules named in earlier revisions of this file now have **no
open alerts** — they were resolved by the two merged PRs, not dismissed:
`py/incomplete-url-substring-sanitization` (17),
`py/request-without-cert-validation` (4), `py/polluting-import` (4),
`py/inheritance/signature-mismatch` (6), and `py/unused-local-variable`,
`py/regex/duplicate-in-character-class`, `py/bad-tag-filter`,
`py/uninitialized-local-variable` (2 each), plus `py/illegal-raise`,
`py/unreachable-except`, `py/imprecise-assert`,
`py/call/wrong-named-argument`, `py/multiple-definition` (1 each).

The 74 Scorecard checks are 69 `PinnedDependenciesID` plus one each of
`BranchProtectionID`, `CodeReviewID`, `CIIBestPracticesID`, `FuzzingID`, and
`TokenPermissionsID`.

## Fixed in `security/codeql-hardening`

These were genuine defects. Each is listed with what actually broke, because
in several cases the impact was worse than the rule name suggests.

### Credential exfiltration — `incomplete-url-substring-sanitization` (1 of 17)

`services/analysis/app/infrastructure/git/repository_fetcher.py`

`clone()` spliced a GitHub App token into the clone URL using a substring
test plus a prefix replace:

```python
if github_token and "github.com" in clone_url:
    clone_url = clone_url.replace("https://github.com", f"...{token}@github.com")
```

`https://github.com.evil.com/attacker/repo.git` satisfies the substring test
*and* matches the replace target, yielding
`https://x-access-token:<token>@github.com.evil.com/...`. Git then
connects to the attacker's host with the token in the userinfo field.

Replaced with `_is_github_host()`, which compares the parsed hostname against
an exact allowlist. Covered by
`services/analysis/tests/infrastructure/test_repository_fetcher_url.py`.

### Lookalike-host acceptance — `incomplete-url-substring-sanitization` (16 of 17)

The remaining 16 alerts were host checks of the form
`"github.com" in url` or `url.startswith("https://docs.python.org")`, used to
decide whether a URL was trusted. Each accepts a lookalike
(`github.com.evil.example`, `docs.python.org.attacker.test`), so a URL that
should have been rejected was treated as trusted.

All 16 now compare the parsed hostname. The AI service uses the shared
`host_matches()` helper from `url_guard.py`; the analysis service uses a
local `_is_github_host()` / `_domain_is()` since it does not depend on the AI
service.

| File | Alerts |
| --- | ---: |
| `ai/app/knowledge_engine/engine.py` | 7 |
| `ai/app/knowledge_engine/ranking/authority.py` | 2 |
| `ai/app/knowledge_engine/sources/community.py` | 2 |
| `ai/app/knowledge_engine/sources/package_registries.py` | 2 |
| `ai/app/knowledge_engine/sources/research_papers.py` | 2 |
| `analysis/app/infrastructure/git/repository_fetcher.py` | 1 (the token bug above) |

`ranking/authority.py` needed more than a suffix swap. It previously did
`any(kw in domain for kw in ["news", "techcrunch", "verge", "arstechnica"])`,
where the bare token `news` matched `notnews.com` and `newsapi.example.com`.
Those now resolve to explicit domains (`techcrunch.com`, `theverge.com`,
`arstechnica.com`) plus a `news.` subdomain prefix check, which is the one
behaviour worth preserving. Since this file scores the authority and freshness
of every knowledge-engine result, it is covered by
`services/ai/tests/test_ranking_authority.py` (37 cases), including that every
lookalike now falls through to the default half-life.

### Weak redirect assertion in a test — `incomplete-url-substring-sanitization` (1)

`services/auth/tests/test_google_oauth.py` asserted
`"accounts.google.com" in response["Location"]`. The failure mode is inverted
from production code: the test would have *passed* had the view redirected
users to `https://accounts.google.com.evil.example`. It now parses the
redirect and asserts `scheme == "https"` and `hostname ==
"accounts.google.com"`, and checks `scope`/`state` as parsed query
parameters rather than substrings.

### Server-side request forgery (4)

A shared guard, `services/ai/app/core/url_guard.py`, now fronts every code
path that fetches a caller-supplied URL. It enforces an `http`/`https`
scheme allowlist and resolves DNS *before* the request, refusing loopback,
link-local, private, reserved, and carrier-grade-NAT space (including
IPv4-mapped IPv6 forms such as `::ffff:169.254.169.254`).

Wired into:

| Site | Alerts |
| --- | --- |
| `application/provisioning/key_validator.py` | 3 × `partial-ssrf` — `custom_url` is a request-body field used directly as the provider base URL |
| `knowledge_engine/multimodal/ingester.py` | 1 × `full-ssrf` — `ingest_url` |
| `application/tools/web_fetch_tool.py` | 2 × `bad-tag-filter` + unvalidated fetch |
| `knowledge_engine/sources/{news,web_search,documentation,community}.py` | `fetch_content` |

Also fixes the case-insensitivity gap behind the two `bad-tag-filter`
alerts: the HTML-stripping fallback used `<script[^>]*>.*?</script>`, so
`<SCRIPT>` and `</script >` survived into model input. The replacement
pattern is `IGNORECASE` and whitespace-tolerant.

Covered by `services/ai/tests/test_url_guard.py` (42 cases).

#### The guard did not survive a redirect

Fixed in `security/codeql-triage-r3`. Guarding the initial URL is not
sufficient when the HTTP client follows redirects on its own, and three
fetchers did:

| Site | Client setting | Flagged? |
| --- | --- | --- |
| `knowledge_engine/multimodal/ingester.py` | `httpx` `follow_redirects=True` | yes — `py/full-ssrf` |
| `application/tools/web_fetch_tool.py` (`WebFetchTool`) | `aiohttp` `allow_redirects=True` | no |
| `application/tools/web_fetch_tool.py` (`NewsFetchTool`) | `aiohttp` `allow_redirects=True` | no |

A public host answers `302` with `Location: http://169.254.169.254/` and
the next request reaches the cloud metadata service unchecked. The
response body was then returned as page text or ingested into the
knowledge base, so this was a full SSRF with the contents read back —
and two of the three sites were not flagged at all.

`url_guard.resolve_redirect()` now resolves a `Location` against the
current URL and re-applies both checks. Redirect following is disabled on
every request and re-implemented in the callers so each hop is validated,
bounded by `MAX_REDIRECT_HOPS`. Public redirects still work, including
relative targets.

The 3 × `py/partial-ssrf` in `key_validator.py` were never affected: its
`httpx` clients leave `follow_redirects` at the `False` default, so the
one `assert_safe_url` call covers the request that is actually made.

Covered by `services/ai/tests/test_redirect_ssrf.py` (21 cases).

### Disabled TLS verification (4) — `request-without-cert-validation`

`knowledge_engine/sources/{news,web_search,documentation,community}.py`
each passed `ssl=False` to `aiohttp`, disabling certificate validation on
content fetches. Removed.

### Wrong HTTP status on GitHub App errors — `unreachable-except` (1)

`services/core/apps/repositories/github_app/views.py`

```python
except GitHubAppError as exc:
    raise NotFound(str(exc)) from exc
except (GitHubAppAPIError, GitHubAppAuthError) as exc:
    raise ValidationError({"detail": str(exc)}) from exc
```

`GitHubAppAPIError` and `GitHubAppAuthError` both subclass `GitHubAppError`,
so the second clause was dead code. Auth failures and API errors were
reported as **404 Not Found** instead of **400**, which told the client to
stop retrying a credential problem. Specific subclasses now precede the
base class.

### `TypeError` instead of a useful error — `illegal-raise` (2)

`services/ai/app/application/analysis/enrichment.py`

`raise last_error` where `last_error: Exception | None`. If `FREE_MODELS`
were ever emptied the loop would not execute and the raise itself would
fail with `TypeError: exceptions must derive from BaseException`. Both
sites now raise the captured error when one exists and a `RuntimeError`
naming the misconfiguration when none does. Both `# type: ignore[misc]`
suppressions removed.

### Internal detail in an API response — `stack-trace-exposure` (1 of 26)

`services/auth/apps/profiles/views.py` caught bare `Exception` on S3 upload
and returned `f"Upload failed: {e}"`, exposing bucket names, object keys,
and SDK internals. The exception is now logged in full and the client gets
a generic message.

### Silent exception swallowing — `empty-except` (24 of 35)

Nearly all were optional-Redis paths (`except Exception: pass`). The
behaviour was correct — a cache failure must not fail a request — but the
swallow made a Redis outage completely invisible. Each now logs at `debug`,
so the failure is diagnosable without changing behaviour.

`knowledge_engine/store/knowledge_indexer.py` was the exception: it swallows
failures around a version-history snapshot, which silently leaves gaps in
version history. That one logs at `warning`.

`apps/notifications/tests/test_tasks.py::test_dispatch_retries_on_failure`
had `except Exception: pass` wrapping the entire call, so it asserted
nothing and would pass whether or not the retry worked. It was rewritten to
assert both that the failing call was attempted and that the original
`Exception("DB error")` propagates.

### Test assertion quality — `imprecise-assert` (1)

`services/auth/tests/test_github_oauth.py` — `assertTrue(len(state) > 20)`
became `assertGreater(len(state), 20)`, which reports both values on
failure.

## Found while reviewing, not flagged by CodeQL

Two defects surfaced while reading the code the alerts pointed at. Neither
has a CodeQL rule, so neither is in the 416.

### Silently discarded a malformed `AI_KEY_ENCRYPTION_KEY`

`services/ai/app/core/encryption.py`:

```python
if len(key_bytes) not in (32, 44):
    key_bytes = Fernet.generate_key()
```

A present-but-wrong-length key produced a **different encrypter on every
process start**. Every provider sub-key encrypted under the bad key became
permanently unreadable, and nothing raised. The length check was also wrong
in the other direction: a 32-byte raw key passed it and then failed inside
`Fernet` with an opaque message.

Now the malformed key raises, naming the cause.

The remediation hint was wrong too, and in `.env.example` as well as in the
error it replaced:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

`token_hex(32)` emits 64 hex characters. `Fernet` requires 32 bytes of
url-safe base64 — 44 characters. Following the documented instructions
produced a key that `Fernet` rejects outright, so the service could not
have booted with the key the docs told you to generate. Corrected to
`Fernet.generate_key().decode()` in all three places.

Two other places assumed a key format that `Fernet` rejects, so a dev stack
or a fresh setup failed in a way that pointed nowhere useful:

- `.env.example` documented the same `token_hex(32)` command and shipped
  `AI_KEY_ENCRYPTION_KEY=your-32-byte-hex-encryption-key` as the placeholder.
  That literal is 36 characters of non-base64 text and is rejected too.
- `docker-compose.dev.yml` defaulted to `dev-encryption-key-32chars!` (27
  characters, despite the name). Since `encryption.py` regenerated on a
  length mismatch, the worker and web container each got a *different*
  random key, so a sub-key stored by one could not be read by the other.
  Replaced with a valid 44-character base64 default, commented as a public
  dev-only value. `docker-compose.yml` already required a real key with no
  default.

Covered by `services/ai/tests/test_encryption.py` (8 cases).

### A test that asserted nothing

`apps/notifications/tests/test_tasks.py::test_dispatch_retries_on_failure`
wrapped the entire call in `except Exception: pass`, so it passed whether or
not the retry worked. Rewritten to assert that the failing call was attempted
exactly once and that the original `Exception("DB error")` propagates.

## Reviewed and dismissed

The reviews recorded in this section were sound, but the corresponding API
dismissals were never filed — so when `security/codeql-triage-r3` started,
these alerts were still open. They were filed from that branch; see *Dismissed
in `security/codeql-triage-r3`* for what actually took effect and for the
Dockerfile pins that were deliberately left open.

### `weak-sensitive-data-hashing` (1)

`services/ai/app/infrastructure/llm/client.py:66`

```python
cache_key = hashlib.sha256(f"{provider}:{api_key}:{base_url or ''}".encode()).hexdigest()[:16]
```

The rule reads this as password hashing. It is not: the value is an
in-process dict key for an SDK client cache, and only the truncated digest is
retained — no plaintext key is stored or logged. SHA-256 is appropriate here.
Switching to bcrypt/argon2 would make every client lookup deliberately slow.

### `stack-trace-exposure` (25 of 26)

The flagged sites catch **narrow domain exceptions** whose messages are
written for the user:

- `KnowledgePermissionError`, `KnowledgeSpaceServiceError`
- `RepositoryPermissionError`, `RepositoryAlreadyConnectedError`
- `WorkspacePermissionError`, `WorkspaceLimitError`, `InvitationError`
- `GitHubAppAPIError`, `GitHubAppAuthError`

Surfacing a domain error message is the point of these handlers; CodeQL
cannot prove the caught type is a domain exception rather than a builtin.
Rewriting them to generic messages would remove useful errors and break the
API contract. The one genuinely broad `except Exception` case was fixed (see
above); `apps/api_keys/views.py` was checked and already correct.

### `call/wrong-arguments` (2), heterogeneous `stage_args` dispatch

`services/analysis/app/application/tasks/pipeline.py` dispatches stages from
a heterogeneous tuple whose element types CodeQL cannot narrow, so it cannot
verify arity. Dispatch is arity-correct at runtime.

### Scorecard `PinnedDependenciesID` (69) and the wider Scorecard set

These contradict each other and, in part, the project's own CI. Pinning
every action to a full commit SHA is what Scorecard's own checks recommend;
the repo already pins the Scorecard action itself
(`ossf/scorecard-action@2d11466`, v2.4.4). Treating these as defects to fix
would trade one check for another rather than improve security. Tracked as
accepted, not suppressed.

Superseded in part from `security/codeql-triage-r3`: the rationale above only
covers the 53 alerts on GitHub Actions `uses:` pins. The 16 on Dockerfile
`FROM` lines make a different claim and are left open — see *Not dismissed:
Docker `FROM` pins*.

### Remaining lint-class noise

`unused-global-variable` (97), `ineffectual-statement` (34),
`unused-import` (15), and the smaller style rules are ruff/CodeQL lint
findings with no security impact. They were triaged in
`security/codeql-triage-r3` rather than deferred to a separate change,
because deferring them left the alert list looking worse than it was. Six of
the 97 turned out to be real dead code and were deleted; the rest are
dismissed with reasons under *Dismissed in `security/codeql-triage-r3`*.

## Fixed in `security/codeql-triage-r3`

### Internal exception text reaching API responses — `stack-trace-exposure`

`core/exceptions.py` gains `log_and_raise()`. It logs the wrapped exception
in full and raises with a stable, caller-safe message. Only exceptions that
wrap third-party text get the generic treatment — the domain exceptions in
`ERROR_TYPE_MAP` carry curated user-facing messages, and replacing those
with generic text would remove the errors the API contract promises.

Applied at the raise sites rather than in the views:

- `repositories/workspaces/members/invitations/views.py` — 4 sites
- `repositories/github_app/client.py` — 8 sites

The GitHub App fix is at the raise site deliberately. Sanitising in the 5
views would have left the taint live for every other consumer; cutting it
where the exception is constructed makes `str(exc)` safe downstream by
construction. The upstream detail still survives in the log `extra=` at
`client.py` lines 136, 180, 205, 256, 275, 325, 341, 395.

Covered by `services/core/tests/test_error_boundaries.py` (19 tests).

### Redundant function-local import — `py/import-and-import-from` (1)

`services/analysis/app/application/analysis/handler.py` imported `gather`
inside the function that used it. Now uses the module-level
`asyncio.gather`. The same commit added 6 tests for `get_job_statistics`,
which had no coverage at all and accepted a `uow` it never used.

### Inconsistent return type — `py/mixed-returns` (2)

`services/ai/app/knowledge_engine/graph/knowledge_graph.py`:
`index_entities` (line 183) and `index_relationships` (line 218) were
annotated `-> list[dict]` but returned `None` on an empty path, so a caller
iterating the result raised `TypeError`. Both now always return a list.
Covered by `services/ai/tests/test_knowledge_graph_contract.py` (9 tests).

### Lint cleanups

`py/unnecessary-lambda` (7) — zero-argument lambdas in test factories
replaced with direct references. `py/unnecessary-lambda` in the knowledge
graph was deliberately not collapsed into a one-liner.

## `log-injection` (62) — triaged in `security/codeql-triage-r3`

This was the largest remaining **security**-class category. All 62 alerts
were classified against what each service's formatter actually renders,
because "a tainted value reaches a log call" is not the same as "a tainted
value reaches a log line".

Two things decide forgeability:

| | Reaches the log line? | Forgeable? |
| --- | --- | --- |
| Value interpolated into the format string | yes | **yes**, if the formatter preserves CR/LF |
| Value passed only through `extra={...}` | **no** | no — never rendered |

`auth` uses the plain `verbose` formatter
(`{levelname} {asctime} {module} {message}`, `auth/settings/base.py:443`),
which renders `message` verbatim. `core` uses `JsonFormatter`, and `ai`
configures structlog's `JSONRenderer`; both escape CR/LF, so a record
cannot be split there even when the value is interpolated.

| Service | Alerts | Interpolated into the format string | Verdict |
| --- | ---: | ---: | --- |
| `auth` | 12 | 2 | 2 forgeable, 10 not |
| `core` | 25 | 0 | none forgeable |
| `ai` | 25 | 25 | none forgeable — renderer escapes CR/LF |

The two genuine findings, both fixed:

- `auth/apps/authentication/oauth/google/views.py` — `error` is
  `request.query_params.get("error")` on an **unauthenticated** endpoint, so
  the value is entirely caller-chosen.
- `auth/apps/api_keys/views.py` — `key_id` is matched by the `<str:key_id>`
  converter, which accepts CR and LF.

Both values are now escaped at the call site, which keeps them readable
rather than dropping them and keeps the traceback on `logger.exception`.

**A logging filter is not a fix here**, for two independent reasons. A
`logging.Filter` cannot satisfy CodeQL at all: the rule's Python sanitizer
is an inline `str.replace()` on the tainted value, which a filter cannot
provide. And the `extra`-only sites do not need one — those values are
never rendered, so there is nothing to strip. The measurements behind the
table are in `auth/apps/authentication/tests/test_log_injection_sanitisation.py`,
which pins both facts and fails if the `verbose` format string ever grows a
field.

`auth`'s `get_client_ip` was reached while reviewing this: it trusted the
first `X-Forwarded-For` hop after `.strip()`, which leaves an embedded
CR/LF intact and any other text too. That value is spliced into the Redis
keys `LoginLockoutManager` counts failed logins against, so it could also
inject key separators. Now validated with `ipaddress` and normalised.
See `security/codeql-triage-r3` for the write-up.

Lockout is still keyed on a header the client controls, so rotating
syntactically valid IPs bypasses the attempt counter. Closing that needs a
proxy-trust list, which is a deployment decision rather than a code fix.

## Dismissed in `security/codeql-triage-r3`

217 alerts were dismissed, each group re-verified against the source before
filing. A dismissal is a permanent public record asserting that the alert is
wrong, so the reasoning is recorded rather than summarised. GitHub caps
`dismissed_comment` at 280 characters, so each comment below is deliberately
terse and points here for the detail.

**Earlier revisions of this file recorded dismissals that were never filed.**
`stack-trace-exposure (25 of 26)` is the clearest case: 24
`stack-trace-exposure` alerts were still open in the API when this branch
started. The rationales were sound; the API calls had not been made.

| Dismissed | Rule | Reason |
| ---: | --- | --- |
| 84 | `py/unused-global-variable` in `migrations/versions/*` | won't fix |
| 7 | `py/unused-global-variable`, module state mutated via `global` | won't fix |
| 10 | `py/unused-import` in `migrations/env.py` | false positive |
| 3 | `py/unused-import`, `if TYPE_CHECKING:` + quoted annotations | false positive |
| 1 | `py/unused-import`, Django migration autodiscovery | false positive |
| 34 | `py/ineffectual-statement`, `...` bodies of `Protocol`/ABC stubs | false positive |
| 9 | `py/import-and-import-from`, module object + symbol in tests | used in tests |
| 5 | `py/undefined-export`, PEP 562 lazy `__all__` | false positive |
| 3 | `py/partial-ssrf` in `key_validator.py` | false positive |
| 3 | `py/stack-trace-exposure` in `knowledge/views/spaces.py` | false positive |
| 1 | `py/stack-trace-exposure` in `api_keys/views.py` | false positive |
| 1 | `py/mixed-returns` in `core/middleware/websocket_auth.py` | false positive |
| 2 | `py/call/wrong-arguments`, heterogeneous `stage_args` dispatch | false positive |
| 1 | `py/weak-sensitive-data-hashing`, in-process cache key | false positive |
| 53 | `PinnedDependenciesID` on GitHub Actions `uses:` pins | won't fix |
| **217** | **total** | |

Three of these are worth stating in full, because the rule name alone
misdescribes them.

**`py/ineffectual-statement` is not a complaint about no-ops.** The flagged
statement is the `...` body of an abstract method: 17 `Protocol` stubs in
`app/domain/contracts/repository_provider.py`, 6 in `storage.py`, 5 in
`apps/authentication/oauth/base.py`, 4 in
`knowledge_engine/sources/base.py`, 1 in `application/tools/base.py`. A `def`
requires a body and `...` is the correct body for one that must never
execute, so there is no spelling that satisfies the rule. The 34th instance
is `tests/test_package_exports.py:56`, which deliberately touches a
non-existent attribute in order to assert that `AttributeError` is raised.

**`py/stack-trace-exposure` in `spaces.py` is safe because of how narrow
the catch is.** Each of the three handlers catches only
`KnowledgePermissionError`, and all five raise sites of that exception —
three in `apps/knowledge/services/space.py`, two in
`apps/knowledge/services/asset.py` — pass a fixed string literal with no
interpolation, so `str(e)` can only ever be one of five constant sentences.
The `api_keys/views.py` case is the same shape but not quite as airtight: it
echoes the caller's rejected scope strings and the valid-scope list, which
is validation feedback rather than internal detail.

**`py/mixed-returns` on `websocket_auth.py:38` is accurate and harmless.**
The function really does mix a bare `return` with
`return await super().__call__(...)`. It does not matter because every bare
`return` is immediately preceded by `await send({"type":
"websocket.close", ...})`, and channels invokes `BaseMiddleware.__call__`
for its effect on `scope` and discards the return value. No caller can
observe a `None` where it expected a value.

### Not dismissed: Docker `FROM` pins

16 of the 69 `PinnedDependenciesID` alerts are on Dockerfile `FROM` lines,
not GitHub Actions `uses:` pins. The rationale above — pinning to a full
commit SHA makes a build reproducible — is true of `uses:` and false of a
floating base-image tag. Those 16 are left open, because a mutable `FROM` is
a real supply-chain finding and the honest answer is to pin by digest, not
to dismiss.

### Two Dockerfiles cannot build

`groupadd`/`useradd` come from `shadow-utils`. Debian-slim images ship it;
**Alpine does not** — Alpine uses BusyBox's `addgroup`/`adduser`. Exactly two
Dockerfiles here are Alpine-based, and both call the Debian binaries:

| File | Base | Line | |
| --- | --- | ---: | --- |
| `frontend/Dockerfile` | `node:18-alpine` | 16 | `groupadd --gid 1001 appgroup` |
| `services/realtime/Dockerfile` | `node:18-alpine` | 10 | `groupadd --gid 1001 appgroup` |

On both, that `RUN` is expected to fail, which also means the following
`USER appuser` is never reached and the image ships running as root — the
exact opposite of what the line is for. This is recorded as
expected-broken, not confirmed-broken: no Docker daemon was available in the
environment where the triage ran, so the build was never executed. The fix is
to switch to `addgroup`/`adduser`, or add `apk add --no-cache shadow`.

The other six Dockerfiles (`core`, `auth`, `ai`, `analysis`, `notifications`)
are `python:3.1x-slim` and use the same `groupadd`/`useradd` idiom correctly,
because Debian-slim does provide it.

Separately, `node:18-alpine` is end-of-life (since 2025-04-30) and floats.
It appears at `frontend/Dockerfile:1` and `:9` and
`services/realtime/Dockerfile:1` — three of the 16 unpinned-`FROM` alerts.
Out of scope for a code-security change; these want a separate decision about
moving both images to a supported Node and pinning by digest.

## Not fixed, and why

- **`failover_engine.py` documents a feature that does not exist.** The
  docstring promises "Periodic rebalance every 5 min (success rate decay)"
  and `__init__` still sets `self._last_rebalance`, but neither
  `_REBALANCE_INTERVAL` nor `_last_rebalance` was ever read. The dead
  constant was deleted; the docstring line and the instance field were left
  in place as the visible marker, because implementing the cycle is a
  feature decision rather than a security fix.
- **`conflict_resolver.py` makes the same kind of claim.** Its docstring
  says conflicts are detected by "embedding similarity + negation patterns",
  and only negation, version and deprecated checks exist. The vestigial
  `_embedder` was removed, but the docstring was deliberately *not*
  rewritten to match it — narrowing a docstring so it agrees with missing
  capability would hide the gap.
- **`assert_safe_url` is open to DNS rebinding.** It resolves the hostname
  and rejects non-public addresses, then the request re-resolves
  independently. That window applies to all 9 of its callers, so it is
  tracked here rather than patched one alert at a time.
- **Lockout evasion via a rotating header.** Lockout is keyed on
  `X-Forwarded-For`, which the client controls, so rotating syntactically
  valid IPs bypasses the attempt counter. Closing that needs a proxy-trust
  list, which is a deployment decision rather than a code fix.