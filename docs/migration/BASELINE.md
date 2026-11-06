# Migration Baseline — Kraivor monorepo restructure

**Purpose.** Freeze the pre-migration state of the repository so that any failure
introduced by the restructure is distinguishable from a failure that already
existed. Every phase gate after this document is compared against these numbers.

| Field | Value |
|---|---|
| Date | 2026-10-09 |
| Branch | `chore/monorepo-restructure` (off `dev`) |
| Base commit | `c2271a4952599367402c73678b5c7e37bc55ccad` |
| Working tree at capture | clean |

## 1. Toolchain

| Tool | Version |
|---|---|
| Node.js | v24.11.0 |
| npm | 11.6.1 |
| pnpm | 9.15.0 |
| uv | 0.11.7 |
| Python | 3.14.2 |
| Docker | 29.7.2 |
| Terraform | **not installed in this environment** |
| GNU `make` | **not installed in this environment** |

## 2. Frontend (`frontend/`)

Run from `frontend/`, mirroring the `frontend-tests` CI job.

| Step | Command | Result |
|---|---|---|
| Clean install | `npm ci` | 0 |
| Lint | `npm run lint` | 0 |
| Typecheck | `npm run typecheck` (`tsc --noEmit`) | 0 |
| Unit tests | `npm test` (`vitest run`) | 0 — **38 files / 588 tests passed** |
| Production build | `npm run build` (`next build`) | 0 — **17 static routes** generated |

Notes (pre-existing, non-blocking):
- `next build` runs ESLint and completes with many `@typescript-eslint/no-unused-vars`
  **warnings** (not errors).
- `npm run lint` prints `next lint is deprecated and will be removed in Next.js 16`.

## 3. Python services (unit tests)

Run from each `services/<name>/`, mirroring the `unit-tests` CI job
(`DJANGO_SETTINGS_MODULE` + `DATABASE_URL=sqlite://:memory:` for the Django
services, then `manage.py migrate` before pytest).

| Service | `uv sync` | `manage.py migrate` | `pytest` | Tests | Coverage | `fail_under` |
|---|---|---|---|---|---|---|
| auth | 0 | 0 | 0 | **422 passed** | 88.59% | 88.0 |
| core | 0 | 0 | 0 | **831 passed, 5 skipped** | 58.25% | 55.0 |
| analysis | n/a | n/a | 0 | **750 passed** | 72.50% | 64.0 |
| ai | n/a | n/a | 0 | **383 passed** | 29.67% | 27.0 |

`services/notifications` and `services/realtime` are excluded — both are being
removed (see `MAP.md` §5). Neither appears in any CI matrix.

## 4. Hard CI gates (these block a merge)

All green before the migration.

| Gate | Command | auth | core | analysis | ai |
|---|---|---|---|---|---|
| ruff | `uv run ruff check .` | 0 | 0 | 0 | 0 |
| bandit | `uv run bandit -r . -x ./tests,./.venv,./migrations --configfile pyproject.toml -ll` | 0 | 0 | 0 | 0 |
| pip-audit | `uv run pip-audit --strict --progress-spinner off` | 0 | 0 | 0 | excluded by design |
| coverage floor | `python ../../scripts/check_coverage.py` | 0 | 0 | 0 | 0 |

`ai` is intentionally excluded from plain `pip-audit`: its CPU-only torch wheel
is not on PyPI, so the audit cannot resolve it. CI runs a torch-stripped variant
(`make security-ai-audit`, POSIX-only).

Repo-level gates:

| Gate | Command | Result |
|---|---|---|
| base images | `python scripts/check_base_images.py` | 0 |
| compose config | `docker compose -f docker-compose.yml config --quiet` | 0 |

`docker compose config` requires `POSTGRES_USER` / `POSTGRES_PASSWORD` (the root
file uses `${VAR:?required}`); both were set to `kraivor` for the check.

## 5. Reported-but-not-gating gates (CI emits `::warning::`)

These already fail on the base commit. They are **recorded, not fixed** — the
restructure must not make them worse, but it is not required to fix them.

| Tool | Command | auth | core | analysis | ai |
|---|---|---|---|---|---|
| black | `uv run black --check --diff .` | 1 | 1 | 1 | 1 |
| isort | `uv run isort --check-only --diff .` | 1 | 1 | 1 | 1 |
| mypy | `uv run mypy .` | 2 | 1 | 1 | 1 |

Confirmed genuine pre-existing drift, not a Windows codepage artifact (re-run
with `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`; still non-zero). Example: black
alone reports 5 files to reformat in `auth`. `mypy` exit 2 in `auth` is the
documented Windows `"Source file found twice under different module names"`
resolution error — see the note in the root `Makefile`.

## 6. Docker image builds

| Image | Command (from `services/<svc>/` or `frontend/`) | Result |
|---|---|---|
| frontend | `docker build -t kraivor-frontend:baseline .` | **0** |
| auth | `docker build -t kraivor-auth:baseline .` | **0** |
| core | `docker build -t kraivor-core:baseline .` | **0** |
| analysis | `docker build -t kraivor-analysis:baseline .` | **0** |
| ai | `docker build -t kraivor-ai:baseline .` | **0** |

All 5 images build on the base commit. Raw service-build log:
`%TEMP%\opencode\kraivor-baseline\docker-services.txt`.

Pre-existing Dockerfile inconsistency observed (to be normalised, not required
for correctness): `auth`/`core` are multi-stage with `uv 0.4.30`; `analysis`/`ai`
are single-stage with `uv 0.11.7`.

## 7. Not executable in this environment

| Gate | Why | Command to run where the tool exists |
|---|---|---|
| terraform fmt | `terraform` not on PATH | `terraform fmt -check -recursive` (in `infra/terraform/`) |
| terraform validate | `terraform` not on PATH | `terraform -chdir=<env> init -backend=false && terraform -chdir=<env> validate` |
| `make` targets | GNU `make` not on PATH | `make check` (the `Makefile` runs under `sh` and `cmd.exe`) |

These are recorded as "unverified locally" rather than "green". The CI `deploy`
and `Docker Validate` workflows are the authority for them.

## 8. Invariants the restructure must preserve

1. **Test totals**: auth 422, core 831 (+5 skip), analysis 750, ai 383, frontend 588.
2. **Coverage floors** in §3 remain met.
3. Every hard gate in §4 stays green.
4. No `::warning::` gate in §5 gets worse.
5. Every image in §6 still builds.

A structural-only change must not move any of these numbers.
