# Phase 2 — Python services → `services/*` (`core`, `analysis`, `ai`, `auth`)

**Status:** complete, awaiting approval to start Phase 3.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).

Phase 2 brought the four Python services onto one consistent layout and tooling.
Each service is a **pure-rename commit** (only `analysis` and `ai` moved) followed
by **content edits** in their own commits, so reviewers can collapse the renames
away. No runtime behavior changed: this phase moved code, renamed the import
package for the two services that moved, deleted duplicated config, and
normalised the Dockerfiles.

`auth` and `core` keep their folder and import package (both are runtime/deploy
names); they got config + Dockerfile normalisation only. `analysis` and `ai`
moved from a top-level `app/` package to a `src/<pkg>/` layout.

## 2e — shared normalisation (applied across 2a–2d)

| Concern | Before | After |
|---|---|---|
| dependency source | `pyproject.toml` + `requirements/*.txt` (stale snapshots) | `pyproject.toml` + `[dependency-groups]` only; `requirements/*.txt` deleted |
| dev dependency source | duplicated `[project.optional-dependencies].dev` **and** `[dependency-groups].dev` | `[dependency-groups].dev` only (PEP 735) |
| uv pin | `0.4.30` (core/auth) vs `0.11.7` (analysis/ai) | `ghcr.io/astral-sh/uv:0.11.7` everywhere |
| sync mode | `uv sync --frozen` | `uv sync --locked` (fail loudly if the lock is stale) |
| build cache | none | `--mount=type=cache,target=/root/.cache/uv` |
| pytest config | `pytest.ini` overriding `[tool.pytest.ini_options]` | single `[tool.pytest.ini_options]` in `pyproject.toml` |
| `.dockerignore` | `.venv/` not always ignored (auth) | `.venv/` + `__pypackages__/` ignored in all four |
| prod image shape | core/auth multi-stage; analysis/ai single-stage | all four multi-stage builder→runtime |

`.flake8` and `tox.ini` were kept in all four services: CI and the root `Makefile`
never invoke them (their settings are duplicated in `pyproject.toml`); removing
them is deferred to Phase 5 (`FOLLOWUPS.md` F6).

## 2a — `services/core/` (Django) — no move

Content commits `46b37e9` (config) + `776ec5d` (Dockerfile).

- Merged `pytest.ini` into `[tool.pytest.ini_options]` (verbatim effective values),
  then deleted `pytest.ini`; `[dependency-groups]` is the single dev source;
  deleted the `requirements/*.txt` snapshots; relocked `uv.lock` (metadata-only).
- Dockerfile: uv `0.4.30` → `0.11.7`; `uv sync --frozen --no-dev` → `uv sync
  --locked --no-dev`; added the uv cache mount. `/app/.venv` layout kept.

## 2b — `services/analysis/` (FastAPI)

Pure rename `5bb0604` (163 files, 0 insertions / 0 deletions), content `fbf81c3`,
normalisation `ad53b2c`.

- `git mv app src/analysis`; import package `app` → `analysis`; pytest
  `pythonpath = ["src"]`; coverage `source` + isort `known_first_party` →
  `["analysis", …]` (dropping the stale top-level `workers/`; `FOLLOWUPS.md` F4).
- Deleted `requirements/*.txt`; dropped the duplicated `dev` extra from
  `[project.optional-dependencies]`, keeping the distinct `prod` extra
  (`FOLLOWUPS.md` F5 / F15); relocked `uv.lock` (debugpy was no longer reachable).
- Prod Dockerfile converted to multi-stage (builder → runtime); `/opt/venv` kept.

## 2c — `services/ai/` (FastAPI + Celery)

Pure rename `c943921` (200 files, 0 insertions / 0 deletions), content `735a172`.

- `git mv app src/ai`; import package `app` → `ai` (628 references over 142 files).
  JSON fixtures under `tests/res/` were left untouched (captured payloads, not
  imports); the false-positive `app.add_middleware / include_router / mount` and
  `celery_app.*` names were preserved.
- Wire-up: `ENV PYTHONPATH=/app/src`; `uvicorn ai.api.main:app` (Dockerfile,
  Dockerfile.dev and `docker-compose.dev.yml`); `celery -A ai.core.celery_app`
  (compose worker + beat); alembic `prepend_sys_path = src`; pytest
  `pythonpath = ["src"]`.
- Deleted `requirements/*.txt`; dropped the duplicated `dev` extra; relocked
  `uv.lock` (metadata-only).

## 2d — `services/auth/` (Django) — no move

Commit `a7b101b`. Folder and `auth.*` package unchanged
(`DJANGO_SETTINGS_MODULE=auth.settings.*`, `ROOT_URLCONF=auth.urls`,
`WSGI_APPLICATION=auth.wsgi.application`, `gunicorn auth.wsgi`).

- Merged `pytest.ini` into `[tool.pytest.ini_options]` (verbatim effective values),
  deleted `pytest.ini`; deleted `requirements/*.txt`; dropped the duplicated `dev`
  extra; relocked `uv.lock` (metadata-only).
- `.dockerignore`: added `.venv/` + `__pypackages__/`.
- Dockerfile + Dockerfile.dev: uv `0.4.30` → `0.11.7`; `--frozen` → `--locked`;
  added the uv cache mount.

## Reference fixups (beyond the MAP table)

| Commit | File | Change |
|---|---|---|
| `3d72cb6` | `fuzzing/fuzz_url_guard.py` | The SSRF fuzz target (a hard CI gate, `.github/workflows/ci.yml`) imported the old `app.core`. Repointed `sys.path` to `services/ai/src` and the import to `ai.core`. Re-ran the corpus gate: **2000 inputs, 0 violations**; `ruff check fuzzing/ scripts/` exit 0. |
| `2186115` | `services/ai/.../test_e2e_pipeline.py`, `services/analysis/.../enrichment_client.py` | stale `services/ai/app/...` path in a docstring; stale `app.*` / `app/...` module names in an architectural comment |

## 2f — gates

Unit tests + coverage, mirroring the CI `unit-tests` job:

| Service | Tests | Coverage | floor |
|---|---|---|---|
| core | **831 passed, 5 skipped** | 58.25% | 55.0 |
| analysis | **750 passed** | 72.50% | 64.0 |
| ai | **383 passed** | 29.67% | 27.0 |
| auth | **422 passed** | 88.59% | 88.0 |

All four match `BASELINE.md` §3 exactly. core and analysis were re-run this
session; ai and auth are their 2c/2d gate results.

Hard gates (`BASELINE.md` §4): `ruff`, `bandit -ll`, and `pip-audit --strict`
(ai torch-stripped) exit 0 for all four services; `scripts/check_coverage.py`
exit 0 for all four. The reported-not-gating gates (§5: `black`, `isort`,
`mypy`) are unchanged from the base commit — still reported, not fixed
(`FOLLOWUPS.md` F1–F3).

Images (`docker build -f services/<svc>/Dockerfile services/<svc>`):

| Service | Image | Build | Smoke |
|---|---|---|---|
| core | `kraivor/core:test` | exit 0 | `manage.py check --settings=core.settings.test` → *System check identified no issues* |
| analysis | `kraivor/analysis:test` | exit 0 | `from analysis.main import app` → *Analysis Service 0.1.0* |
| ai | `kraivor/ai:test` | exit 0 | `from ai.api.main import app` → *Kraivor AI Service 0.1.0* (boots once `AI_KEY_ENCRYPTION_KEY` is set; no env needed for the other settings) |
| auth | `kraivor/auth:test` | exit 0 | `manage.py check` (test settings) → *System check identified no issues* |

Compose (`docker compose … config --quiet`):

| File | Result |
|---|---|
| `docker-compose.yml` | exit 0 |
| `docker-compose.dev.yml` | exit 0 |
| `docker-compose.prod.yml` | exit 1 — **pre-existing**: `service "core-worker" has neither an image nor a build context specified`; needs prod env vars; file untouched by this branch (`FOLLOWUPS.md` F14) |

## Reference sweep

A repo-wide sweep for the old paths returns nothing outside the intentional KEEP
list:

- `app.api.main` / `app.main:app` / `app.core.celery_app` — only in
  `docs/migration/MAP.md` (the plan itself) and one captured-payload JSON fixture
  under `services/ai/tests/res/`.
- `services/ai/app` / `services/analysis/app` — only in `docs/` (Phase 5 scope)
  and the same fixture.

## Follow-ups / observations

- **Local Docker Desktop instability.** The Linux engine crashed several times
  during this phase (twice mid-build with `rpc error … EOF`, then the
  `dockerDesktopLinuxEngine` pipe was absent). This is the local Windows
  environment, not the repo: builds were retried to completion and every result
  in this document is from a successful run. No repo change.
- `docker compose config` prints `The "_pqiS" variable is not set` on every file
  because the untracked local `.env` `SECRET_KEY` contains a literal `$`; local
  hygiene only (`FOLLOWUPS.md` F11 note), the tracked repo is unaffected.
- `terraform` / `make` are still not installed locally, so those gates remain
  CI-only (unchanged from baseline).

## Commits (nothing pushed)

1. `46b37e9` — 2a core config
2. `776ec5d` — 2a core Dockerfile
3. `5bb0604` — 2b analysis pure rename
4. `fbf81c3` — 2b analysis content
5. `c943921` — 2c ai pure rename
6. `735a172` — 2c ai content
7. `a7b101b` — 2d auth config + Dockerfile
8. `ad53b2c` — 2e analysis dev-extra + requirements cleanup
9. `3d72cb6` — fuzzing target fix (ai rename fallout)
10. `2186115` — stale comment/docstring refs
11. this `PHASE-2.md`

Next: **Phase 3** — `infra/` verification pass (see `MAP.md`).
