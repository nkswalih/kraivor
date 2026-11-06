# Phase 5 - docs, DX, and tooling consistency

**Status:** complete, awaiting approval.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).

Phase 5 is the last structural phase. It changes documentation layout,
developer tooling, root configuration, and the last stale CI references. It
changes **no application source** in `apps/web` or `services/*`.

## Scope (from `MAP.md`)

| Item | Action |
|---|---|
| docs reorg | `docs/{architecture,services,development,operations,api}`; fix stale links |
| per-service Makefiles | uniform targets; root orchestrates without duplicated lines |
| root config | `.gitignore`, root `pyproject.toml` |
| CI prose | remove last stale service traces |
| FOLLOWUPS | log unrelated pre-existing issues, do not fix |

## Commits (nothing pushed)

| Commit | What |
|---|---|
| `1d88fbe` | pure rename of 19 tracked docs files, 0 insertions/deletions |
| `fcbd974` | README/doc links, docs index, corrected prerequisites and test examples |
| `cdff0ad` | uniform per-service Makefiles + generated root orchestration |
| `7a7a074` | root config: drop `ruff.toml` and the stub `uv.lock`; trim `.gitignore` |
| `8581d36` | remove stale CI/service/path traces; resolve F8/F9; log F18 |
| this file | Phase 5 record |

## Docs map

| Before | After |
|---|---|
| `docs/ARCHITECTURE.md`, `docs/KRAIVOR_COMPLETE_DOCUMENTATION.md` | `docs/architecture/` |
| `docs/AUTH_SERVICE.md`, `docs/CORE_SERVICE.md` | `docs/services/` |
| `docs/chat/` (5 files) | `docs/services/chat/` (kept together so their relative links stay valid) |
| `docs/CI-MIGRATION-FIXES.md`, `CI-VS-DOCKER.md`, `DOCKER.md`, `KRV-011.md` | `docs/development/` |
| `docs/CODEQL-TRIAGE.md`, `docs/DEPLOYMENT.md` | `docs/operations/` |
| `docs/postman/` (4 files) | `docs/api/postman/` |
| `docs/assets/`, `docs/migration/` | unchanged |
| `docs/handbook/`, `docs/documents/` | unchanged - untracked/local-only (`.gitignore`) |

`docs/README.md` is new and indexes every tracked category.

`docs/operations/CODEQL-TRIAGE.md` is a historical record of findings from the
pre-migration tree. Its paths are intentionally left as written; the index and
the file itself say so.

## Makefile target set

Every service has the same targets:

`install dev lint typecheck test build security format format-fix coverage check sh clean`

| Target | Behaviour |
|---|---|
| `install` | `uv sync --locked` |
| `dev` | `docker compose -f ../../docker-compose.dev.yml up --build <service>` |
| `lint` | `uv run --locked ruff check .` (hard gate) |
| `typecheck` | `uv run --locked mypy .` (advisory, mirrors the `::warning::` CI step) |
| `test` | CI's pytest invocation + `scripts/check_coverage.py` (hard gate) |
| `build` | `docker build -f Dockerfile`, service dir as context (matches `docker.yml`) |
| `security` | bandit + pip-audit (hard gates); `ai` runs bandit only |
| `format` | `black --check --diff` + `isort --check-only --diff` (advisory, no writes) |
| `format-fix` | rewrite with black + isort |
| `coverage` | coverage report without `--maxfail` |
| `check` | `lint test security` |
| `sh` | shell into the running dev container |
| `clean` | remove local caches and reports |

Notes:

- `auth` maps to the compose service `identity`; the other three map to
  themselves. The old Makefiles' `docker compose exec auth` could never work.
- The root Makefile generates one recursive rule per aggregate from
  `SERVICES`, so adding a service is a one-line change. Recursive make parses
  under both `sh` and `cmd.exe`; a `for ... done` loop does not.
- Root `install` and `build` also cover `apps/web`; `frontend-check` remains
  CI's typecheck/test/build trio.
- Root `dev` now uses `docker-compose.dev.yml` (the full local stack) instead of
  the base compose file.

## Root config

- **`ruff.toml` deleted.** Its explanation moved into the root
  `pyproject.toml` `[tool.ruff]` block. The rule set is unchanged; services
  still resolve their own config. `ruff check fuzzing scripts` from the root
  exits 0 against the consolidated config.
- **Root `uv.lock` deleted.** It was a 55-byte stub with no root `[project]`;
  every service owns its own lock and no root command runs `uv sync`/`uv run`.
- **`.gitignore` trimmed.** Removed the stale scratch-filename list (none of
  those files exist at the root) and duplicated rules (`*/.coverage`,
  `apps/web/coverage/`, a second `*.tsbuildinfo`, `.DS_Store`, duplicate
  `dist/`/`build/`). Kept the local-only doc directories and scoped the
  existing `services/analysis/docs/progress.md` under
  `services/analysis/docs/`, so nothing new is exposed.

## CI and stale traces

- `.github/actions/setup/action.yml`: default Python `3.14`, uv pinned to
  `0.11.7`, and `uv sync --locked` (`dev` is the default group). `--frozen`
  would have used a stale lock silently.
- `scripts/check_base_images.py`: removed `notifications` from `SERVICES`.
- `.github/dependabot.yml`: npm prefix `chore(frontend/deps)` ->
  `chore(web/deps)`.
- `CODEOWNERS` / `.github/labeler.yml`: removed dead `/k8s/`, `/terraform/`
  and `helm/**/*` patterns (code lives under `infra/`). Resolves F8 and F9.
- `FOLLOWUPS.md`: added F18 and the Phase 5 notes.

## Verification

| Check | Result |
|---|---|
| `make -n check` / `make -n install` / `make -n format-fix` | expand to the expected per-service commands; no duplicate gate runs |
| `make -C services/core lint` | **exit 0** - `All checks passed!` |
| `make -C services/core test` | **exit 0** - 831 passed, 5 skipped; 58.25% (floor 55%); `check_coverage.py` reports 58.25% |
| `make -C services/core format` | **exit 0** - advisory; black/isort findings reported, not fatal |
| `make -C services/core typecheck` | **exit 0** - advisory; 2690 mypy errors reported, not fatal (matches CI) |
| `make -C services/ai help` | renders all 13 targets without literal quotes under `cmd.exe` |
| `scripts/check_base_images.py` | exit 0 - digests pinned, Python floor >= 3.14 |
| changed YAML (`.github/actions/setup`, `dependabot`, `labeler`) | 3/3 parse |
| `docker compose -f docker-compose.yml config --quiet` | exit 0 |
| `docker compose -f docker-compose.dev.yml config --quiet` | exit 0 |
| `docker compose -f docker-compose.prod.yml config --quiet` | exit 1 - pre-existing F14; file untouched |
| relative Markdown links | 45 links across 33 tracked files; 1 missing = F18 (`SECURITY.md` -> `HALL_OF_FAME.md`) |
| `ruff check fuzzing scripts` | exit 0 from the root `pyproject.toml` |
| `git diff --check` | clean |

Only core's suite was re-run: Phase 5 touched no Python or TypeScript source,
so auth/analysis/ai results from Phase 2 still stand. Core was chosen to
exercise the new `test` target (migrate -> pytest -> coverage floor) end to end.
`pnpm install` and the frontend build were not re-run because no dependency or
web file changed.

## Decisions and deviations

- **`packages/contracts` was skipped** (Phase 4 audit: no genuine shared
  duplication). See `PHASE-4.md`.
- **`format` is a check, not a rewrite**, matching CI's `::warning::` step and
  the old root `format`; `format-fix` is the explicit rewrite target.
- **`typecheck` and `format` are advisory.** They do not fail `check`, because
  their CI steps do not block a merge.
- **`.flake8` and `tox.ini` are kept.** They are unused by CI and the root
  Makefile, but removing them is an unrelated cleanup (F6).
- **`operations/CODEQL-TRIAGE.md` keeps its old paths** as a historical record.

## Follow-ups

- **F8 / F9** resolved by this phase (dead CODEOWNERS/labeler patterns).
- **F18** added: `SECURITY.md` links to `HALL_OF_FAME.md`, which has never been
  tracked on any branch.
- **F14** remains: `docker-compose.prod.yml` needs a profile to validate. This
  branch does not touch that file.

Next: approval, then the final branch gate and merge preparation.
