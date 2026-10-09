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
| F4 | analysis config | `[tool.coverage.run].source = ["app","workers"]` and isort `known_first_party = ["app","workers","tests"]` reference a top-level `workers/` that does not exist (only `app/workers/`) | `services/analysis/pyproject.toml:68,135`; dir listing has no `workers/` | drop the stale `workers` entries | low |
| F5 | dependency duplication | `analysis` (and `ai`) declare dev deps in **both** `[project.optional-dependencies].dev` and `[dependency-groups].dev` | `services/analysis/pyproject.toml:28–49,164–186` | keep one source | low |
| F6 | exclusions | `services/analysis/.flake8`, `pytest.ini`, `tox.ini` coexist with equivalent `pyproject.toml` config | service dir listings | consolidate (candidate for Phase 5, or leave) | low |
| F7 | stray artifacts | tracked/leftover test outputs: `frontend/public/Screenshot 2026-05-25 212539.png`, `services/ai/tests/res/*.json`, `services/analysis/test.db` | file listing / `BASELINE` scan | remove in a cleanup PR | low |
| F8 | CODEOWNERS | patterns `/k8s/` and `/terraform/` match no directory (code lives under `infra/`) | `CODEOWNERS:32–33` | already partly superseded by `/infra/`; drop the two dead lines | low |
| F9 | labeler | `helm/**/*`, `terraform/**/*`, `k8s/**/*` patterns match nothing (no such dirs) | `.github/labeler.yml:57–59` | drop dead patterns | low |
| F10 | frontend lint | `next build` completes with many `@typescript-eslint/no-unused-vars` warnings; `next lint` prints a deprecation notice | `BASELINE.md` §2 | clean unused vars; migrate off `next lint` before Next 16 | low |
| F11 | local env | untracked `.env`, `.env.bak-20260930-233203`, `.env.production` and a repo-root `.venv/` exist on disk (uv warns `VIRTUAL_ENV` mismatch) | `BASELINE` capture; `.gitignore:2` | local hygiene; delete stale `.env.bak-*` and root `.venv` | info |
| F12 | dead scaffolds | `services/notifications` (all `app/` 0-byte; `fail_under=90` passes vacuously) and `services/realtime` (Dockerfile runs `npm install` with no `package.json`) fail to build | `BASELINE`; service listings | **resolved by this migration** (Phase 0.5 removes both) | — |
| F13 | uv version drift | core/auth Dockerfiles use `ghcr.io/astral-sh/uv:0.4.30`; analysis/ai use `0.11.7` | `Dockerfile*` grep | **normalised by this migration** (Phase 2e) | — |
| F14 | compose | `docker-compose.prod.yml` cannot be validated with `docker compose config`, alone or layered on the base: it sets `profiles: ["removed"]` on `postgres`/`redis`/`kafka`/`dynamodb-local`/`frontend`, so dependents such as `ai` fail with `depends on undefined service "postgres"` | `docker-compose.prod.yml:12–26`; observed in Phase 0.5 | document that prod validation needs `--profile`, or decouple `depends_on` from profiled infra | low |

## Notes

- F12/F13 are listed for completeness; they are addressed by the restructure
  itself, not deferred.
- Any new unrelated finding discovered during Phases 0.5–5 is appended here
  rather than fixed in place.
