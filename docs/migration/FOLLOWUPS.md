# Migration Follow-ups — unrelated pre-existing issues

Per the migration ground rules, anything found that is **not** part of the
structure change is logged here and **not fixed**. Each entry is evidence-backed.
Severity is about impact, not about whether it blocks this migration.

## Open

| # | Area | Finding | Evidence | Suggested (later) fix | Severity |
|---|---|---|---|---|---|
| F1 | formatting | `black --check` fails on the base commit in all four Python services | `BASELINE.md` §5; e.g. 5 files in `auth` | run `black` repo-wide in a dedicated formatting PR | low |
| F2 | imports | `isort --check-only` fails on the base commit in all four services | `BASELINE.md` §5 | dedicated `isort` PR; note the Windows `PYTHONUTF8=1` requirement | low |
| F3 | typing | `mypy .` fails on the base commit in all four services; `auth` exits 2 with `"Source file found twice under different module names: logging_utils and auth.logging_utils"` | `BASELINE.md` §5; root `Makefile` note | resolve `auth` module-root config so local output matches CI | medium |
| F4 | analysis config | `[tool.coverage.run].source` and isort `known_first_party` referenced a top-level `workers/` that does not exist (only `app/workers/`) | `services/analysis/pyproject.toml` at base | **resolved by this migration** (Phase 2b: `source = ["analysis"]`, `known_first_party = ["analysis","tests"]`) | — |
| F5 | dependency duplication | `core`/`analysis`/`ai`/`auth` declared dev deps in **both** `[project.optional-dependencies].dev` and `[dependency-groups].dev` | service pyprojects at base | **resolved by this migration** (Phase 2a/2c/2d/2e: `[dependency-groups].dev` is the single dev source for all four; `analysis` keeps its distinct `prod` extra — see F15) | — |
| F6 | exclusions | `services/*/.flake8` and `tox.ini` coexist with equivalent `pyproject.toml` config | service dir listings | `pytest.ini` consolidated into `pyproject.toml` for all four services in this migration (Phase 2a–2d); `.flake8`/`tox.ini` intentionally kept — unused by CI and the root `Makefile` (candidate for Phase 5) | low |
| F7 | stray artifacts | tracked/leftover test outputs: `frontend/public/Screenshot 2026-05-25 212539.png`, `services/ai/tests/res/*.json`, `services/analysis/test.db` | file listing / `BASELINE` scan | remove in a cleanup PR | low |
| F8 | CODEOWNERS | patterns `/k8s/` and `/terraform/` match no directory (code lives under `infra/`) | `CODEOWNERS:32-33` | **resolved by this migration** (Phase 5: both dead lines removed; `/infra/` remains) | - |
| F9 | labeler | `helm/**/*`, `terraform/**/*`, `k8s/**/*` patterns match nothing (no such dirs) | `.github/labeler.yml:57-59` | **resolved by this migration** (Phase 5: dead patterns removed; only `infra/**/*` remains) | - |
| F10 | frontend lint | `next build` completes with many `@typescript-eslint/no-unused-vars` warnings; `next lint` prints a deprecation notice | `BASELINE.md` §2 | clean unused vars; migrate off `next lint` before Next 16 | low |
| F11 | local env | untracked `.env`, `.env.bak-20260930-233203`, `.env.production` and a repo-root `.venv/` exist on disk (uv warns `VIRTUAL_ENV` mismatch) | `BASELINE` capture; `.gitignore:2` | local hygiene; delete stale `.env.bak-*` and root `.venv` | info |
| F12 | dead scaffolds | `services/notifications` (all `app/` 0-byte; `fail_under=90` passes vacuously) and `services/realtime` (Dockerfile runs `npm install` with no `package.json`) fail to build | `BASELINE`; service listings | **resolved by this migration** (Phase 0.5 removes both) | — |
| F13 | uv version drift | core/auth Dockerfiles use `ghcr.io/astral-sh/uv:0.4.30`; analysis/ai use `0.11.7` | `Dockerfile*` grep | **normalised by this migration** (Phase 2e) | — |
| F14 | compose | `docker-compose.prod.yml` cannot be validated with `docker compose config`, alone or layered on the base: it sets `profiles: ["removed"]` on `postgres`/`redis`/`kafka`/`dynamodb-local`/`frontend`, so dependents such as `ai` fail with `depends on undefined service "postgres"` | `docker-compose.prod.yml:12–26`; observed in Phase 0.5 | document that prod validation needs `--profile`, or decouple `depends_on` from profiled infra | low |
| F15 | optional extras | `analysis` still declares a `prod` extra (`uvloop`, `httptools`) that **nothing installs**: every image/CI path runs `uv sync --locked [--no-dev]` with no `--extra`/`--all-extras`, and `uvicorn[standard]` already pulls both into the main set | `services/analysis/pyproject.toml`; `services/*/Dockerfile*` `uv sync` lines | drop the `prod` extra, or switch the prod image to `--extra prod` if it is meant to be installed | low |
| F16 | analysis schemas | `HealthResponse` is defined twice: `api/routers/health.py` (with `dependencies`) and `api/schemas/common.py` (without); the router uses its local copy and the `schemas` export is unused by it | `git grep -n HealthResponse -- services/analysis/src` | keep one definition — extend `common.HealthResponse` with `dependencies` and import it | low |
| F17 | contracts | `apps/web` hand-maintains TypeScript types that mirror service models: 38 exported TS names also name a Python class and nothing generates them, so drift is undetected | `docs/migration/PHASE-4.md` (Phase 4 audit) | adopt OpenAPI/JSON-Schema codegen if drift becomes a problem (out of scope here - "no new frameworks") | info |
| F18 | docs link | `SECURITY.md` links to `HALL_OF_FAME.md`, which has never been tracked on any branch | `SECURITY.md:102`; `git log --all -- HALL_OF_FAME.md` is empty | add the file, or rewrite the sentence to describe the policy without a link | low |

## Notes

- F12/F13 are listed for completeness; they are addressed by the restructure
  itself, not deferred.
- Any new unrelated finding discovered during Phases 0.5–5 is appended here
  rather than fixed in place.
- Phase 2 note: `docker compose config` prints
  `The "_pqiS" variable is not set` on every compose file - the untracked local
  `.env` `SECRET_KEY` contains a literal `$`, which compose tries to
  interpolate (local env hygiene, see F11; the tracked repo is unaffected).
- Phase 5 note: the docs reorg moved tracked files into
  `docs/{architecture,services,development,operations,api}` and added
  `docs/README.md`. `docs/handbook/` and `docs/documents/` were already
  local-only (ignored) and were not moved or tracked.
- Phase 5 note: the per-service Makefiles now run locally with
  `uv run --locked`; `typecheck` and `format` remain advisory because their CI
  steps are `::warning::`, and `format-fix` is the opt-in rewrite target.
- Phase 5 note: `operations/CODEQL-TRIAGE.md` is a historical record and still
  names pre-migration paths on purpose (see the note in `docs/README.md`).
- Phase 5 note: `docker compose -f docker-compose.prod.yml config` still exits 1
  (F14, unchanged); the main and dev compose files both validate.
