# Migration Map — Kraivor monorepo restructure

**Scope:** folder structure, package/workspace layout, and tooling consistency
only. **Zero behaviour change.** No framework, DB, queue, or package-manager
additions. Core keeps every feature.

Companion: [`BASELINE.md`](./BASELINE.md) (frozen pre-migration numbers).

| Field | Value |
|---|---|
| Branch | `chore/monorepo-restructure` |
| Base | `c2271a4952599367402c73678b5c7e37bc55ccad` |
| Infra name | **stays `infra/`** (not renamed to `deploy/`) |

## Risk legend

| Code | Meaning | Rollback |
|---|---|---|
| **L** | Mechanical path move (`git mv`) | `git mv` back; no content edits |
| **M** | Move + bounded content edits (paths/imports/config) | revert the phase commit (moves are pure-rename commits, edits separate) |
| **H** | Touches a runtime entrypoint, CI, or image build | full gate re-run + revert phase commits |

---

## Target end state

```
apps/web/                                  ← frontend/
services/auth/          (folder name kept; runtime/deploy name stays "identity")
services/core/
services/analysis/
  src/analysis/                            ← app/   (import package = analysis)
services/ai/
  src/ai/                                  ← app/   (import package = ai)
packages/contracts/                        ← only if duplication is proven (Phase 4)
infra/                                     ← KEEPS ITS NAME
  docker/  kubernetes/  terraform/  lambda/
docs/{architecture,services,development,operations,api}/
docs/migration/{BASELINE,MAP,PHASE-*,FOLLOWUPS}.md
tests/                                     ← only if real cross-service tests exist
pnpm-workspace.yaml  turbo.json  package.json        (root, new)
docker-compose.yml  docker-compose.dev.yml  docker-compose.prod.yml   (root, kept)
```

Removed: `services/notifications/`, `services/realtime/` + their k8s manifests +
the two ingress routes.

---

## Phase 0.5 — Remove dead services

Both are non-functional scaffolds and appear in **no** CI matrix, **no** compose
file, and **no** lockstep build. `services/notifications/app/` is entirely 0-byte;
`services/realtime/` has no `package.json` yet its Dockerfile runs `npm install`
(pre-existing broken build).

### 0.5a `git rm -r` (tracked files only)

| Path | Tracked files | Risk |
|---|---|---|
| `services/notifications/` | 19 (`app/**` 0-byte, `Dockerfile`, `Makefile`, `pyproject.toml`, `tox.ini`, `.flake8`, `.pre-commit-config.yaml`, `requirements/{base,dev,prod}.txt`, `uv.lock`, `README.md`) | L |
| `services/realtime/` | 7 (`src/events/*.js`, `src/socket/*.js`, `tests/__init__.py`, `Dockerfile`) | L |

Untracked artifacts under them (`.venv/`, `.ruff_cache/`, `.coverage`) are **not**
in git and are left on disk; they are not part of the commit.

### 0.5b k8s + ingress

| File | Action | Detail |
|---|---|---|
| `infra/kubernetes/services/notifications/deployment.yaml` | delete | Deployment+Service `notifications-service:8005` |
| `infra/kubernetes/services/realtime/deployment.yaml` | delete | Deployment+Service `realtime-service:8006` |
| `infra/kubernetes/infrastructure/ingress.yaml` | edit | remove path `/api/notifications` → `notifications-service:8005` (L41–47) |
| `infra/kubernetes/infrastructure/ingress.yaml` | edit | remove path `/ws` → `realtime-service:8006` (L48–54) |

Kept in ingress: `/api/auth`, `/api/workspace`, `/api/analysis`, `/api/ai`,
`kraivor.com /` → `frontend-service:3000`.

### 0.5c Reference edits

| File:line | Current | Change | Risk |
|---|---|---|---|
| `scripts/check_base_images.py:196` | `("frontend", "services/realtime")` | drop `services/realtime` (Phase 1 changes `frontend`→`apps/web`) | L |
| `scripts/check_coverage.py:7` | docstring names `services/notifications` as the 0-statement example | reword to a non-service-specific example | L |
| `docs/ARCHITECTURE.md:16–17,23` | service table rows for `realtime`/`notifications` | delete rows + scaffold note | L |
| `README.md:180–183` | notifications scaffold note + link | delete note | L |
| `docs/DEPLOYMENT.md:121` | notifications scaffold note | delete | L |
| `.github/workflows/ci.yml:228` | prose comment about notifications `fail_under` | drop stale sentence | L |

### 0.5d Explicitly KEPT (not the dead service)

- `infra/terraform/modules/sqs/main.tf` — `kraivor-notifications-*` queue + DLQ.
- `infra/terraform/modules/lambda-notifications/` — notification Lambda.
- `infra/lambda/notifications/` — Lambda source.
- `docs/CODEQL-TRIAGE.md` — historical record, left as-is by decision.

### 0.5e Gate

- `python scripts/check_base_images.py` → 0
- `python scripts/check_coverage.py` from each of the four service dirs → 0
- `docker compose -f docker-compose.yml config --quiet` → 0
- `grep` proves no remaining `services/notifications`, `services/realtime`,
  `notifications-service`, `realtime-service` outside the KEEP list.

---

## Phase 1 — `frontend/` → `apps/web/`

### 1a Move (pure rename)

`git mv frontend apps/web`, and add `pnpm-workspace.yaml`, `turbo.json`, root
`package.json` in a **separate** commit.

### 1b npm → pnpm (content, separate commit)

| Item | Current | Target |
|---|---|---|
| lockfile | `frontend/package-lock.json` | `apps/web/pnpm-lock.yaml` (delete package-lock) |
| workspace | none | `pnpm-workspace.yaml` members `apps/*`, `packages/*` |
| task runner | none | `turbo.json`, root `package.json` scripts |
| Dockerfile | `COPY package*.json` + `npm ci`/`npm run build` | pnpm: `corepack enable` + `pnpm install --frozen-lockfile` + `pnpm build` |
| CI | `npm ci/run build/test` | `pnpm install --frozen-lockfile` + `pnpm -C apps/web …` |
| Makefile | `cd frontend && npm run …` | `pnpm -C apps/web …` |

> `pnpm-workspace.yaml` members = `apps/*` + `packages/*` only. There is no
> `services/realtime` member.

### 1c Reference edits

| File:line | Current | Change | Risk |
|---|---|---|---|
| `docker-compose.yml:416` | `context: ./frontend` | `context: ./apps/web` | M |
| `.github/workflows/ci.yml:352,361,385,394` | `working-directory: frontend`, `frontend/package-lock.json` | `apps/web`, `apps/web/pnpm-lock.yaml` | M |
| `.github/workflows/license-check.yml:9–10` | paths `frontend/package.json`, `frontend/package-lock.json` | `apps/web/…` pnpm paths | L |
| `.github/dependabot.yml:37,46,50` | dir `/frontend`, prefix/label `frontend` | `/apps/web`, `apps/web` | L |
| `.github/labeler.yml:7,66,67` | `frontend/**/*`, `frontend/package*.json` | `apps/web/**/*`, pnpm lock | L |
| `CODEOWNERS:11` | `/frontend/` | `/apps/web/` | L |
| `.gitignore:89` | `frontend/coverage/` | `apps/web/coverage/` | L |
| `Makefile:117,119,121` | `cd frontend && npm …` | pnpm in `apps/web` | M |
| `infra/kubernetes/services/frontend/deployment.yaml` | image `kraivor-frontend` | unchanged (no path; name stays) | — |

> `docker-compose.prod.yml` does not build the frontend (Vercel hosts it) — no change.
> `docker-compose.dev.yml` does not run the frontend container — no change.

### 1d Gate

Frontend `pnpm install --frozen-lockfile`, lint, typecheck, test (**588 tests**),
`pnpm build` (17 routes) all 0; `docker build` of `apps/web` → 0; compose config 0.

---

## Phase 2 — Python services

Order: **core → analysis → ai → auth** (matches locked plan). Each service is its
own commit: pure-rename first, then content edits.

### 2a `services/core/` — no move (folder + import package kept)

Dependency/config cleanup only. **No feature removal** (core owns the real
notifications app and the Channels realtime consumer — both stay).

| Item | Action | Risk |
|---|---|---|
| `requirements/{base,dev,prod}.txt` | delete after Docker/CI stop referencing; single source = `pyproject.toml` + `[dependency-groups]` | M |
| config duplication | consolidate `pytest.ini`/`tox.ini`/`.flake8` into `pyproject.toml` where safe | M |
| Dockerfile | normalise to the common pattern + one uv version; `uv sync --locked` | H |

### 2b `services/analysis/`

| Item | Current | Target | Risk |
|---|---|---|---|
| package dir | `app/` | `src/analysis/` | L |
| import package | `app` | `analysis` | H |
| imports | `from app.…` ×606 in 147 files | `from analysis.…` | H |
| uvicorn (compose) | `app.main:app` (`docker-compose.dev.yml:375`) | `analysis.main:app` | H |
| uvicorn (image) | `uvicorn app.main:app` (`Dockerfile:29`, `Dockerfile.dev:54`) | `analysis.main:app` | H |
| Dockerfile env | `ENV PYTHONPATH=/app` (`Dockerfile:9`, `Dockerfile.dev:32`) | `ENV PYTHONPATH=/app/src` | H |
| coverage source | `["app","workers"]` (L135) | `["analysis"]` (`workers` is stale — see FOLLOWUPS) | M |
| isort `known_first_party` | `["app","workers","tests"]` (L68) | `["analysis","tests"]` | L |
| mypy overrides | `app.api.schemas.*` … (L85–98) | `analysis.…` | L |
| `app/config.py` shim | `from app.core.config import …` | `from analysis.core.config import …` (shim stays) | L |
| alembic | `migrations/alembic.ini` | keep; verify `script_location` after move | M |

### 2c `services/ai/`

| Item | Current | Target | Risk |
|---|---|---|---|
| package dir | `app/` | `src/ai/` | L |
| import package | `app` | `ai` | H |
| imports | `from app.…` ×595 in 140 files | `from ai.…` | H |
| uvicorn (compose) | `app.api.main:app` (`docker-compose.dev.yml:428`) | `ai.api.main:app` | H |
| uvicorn (image) | `uvicorn app.api.main:app` (`Dockerfile:37`, `Dockerfile.dev:112`) | `ai.api.main:app` | H |
| celery worker/beat | `-A app.core.celery_app` (`docker-compose.dev.yml:436,463`) | `-A ai.core.celery_app` | H |
| alembic | `alembic.ini` (root) | keep location | M |
| Dockerfile env | `ENV PYTHONPATH=/app` (`Dockerfile:15`, `Dockerfile.dev:71`) | `ENV PYTHONPATH=/app/src` | H |
| coverage/mypy/ruff `app` refs | in pyproject | `ai` | L |

### 2d `services/auth/` — no move (folder kept)

Folder stays `services/auth/`; `identity` remains a runtime/deploy name only.
`DJANGO_SETTINGS_MODULE=auth.settings.*`, `ROOT_URLCONF=auth.urls`,
`WSGI_APPLICATION=auth.wsgi.application`, `gunicorn auth.wsgi` — **all unchanged**.
Dep/config cleanup only, same as core.

### 2e Shared Dockerfile/pyproject normalisation (applies to 2a–2d)

| Item | Current | Target |
|---|---|---|
| uv image | core/auth `0.4.30`; analysis/ai `0.11.7` | one pinned version |
| stages | core/auth multi-stage; analysis/ai single-stage | one consistent pattern |
| sync mode | `uv sync --frozen --no-dev` | `uv sync --locked --no-dev` |
| dep source | `pyproject.toml` + `requirements/*.txt` | `pyproject.toml` + `[dependency-groups]` only |
| dev deps | `[project.optional-dependencies].dev` **and** `[dependency-groups].dev` both present (analysis) | single source |

### 2f Gate (after each service)

`uv sync` → `pytest` (auth 422 / core 831 / analysis 750 / ai 383, coverage floors
met) → ruff/bandit/pip-audit/check_coverage → `docker build` + container start →
`docker compose config`. No `::warning::` gate may regress.

---

## Phase 3 — `infra/` stays (verification pass)

No `git mv`. Terraform, k8s, `lambda/`, `dev`/`prod`, addresses all unchanged.

| Item | Action |
|---|---|
| k8s deployments | notifications/realtime already removed in 0.5b |
| ingress | routes already removed in 0.5b |
| path refs broken by Phases 1–2 | fix any `frontend/`/`app/` path in `infra/**` (none expected) |
| `docker-compose*.yml` mounts | verify `./infra/docker/*` mounts still resolve |

### 3 Gate

`terraform fmt -check -recursive` + `init -backend=false && validate` per env
(CI runner; not installed locally) and `docker compose config` → 0.

---

## Phase 4 — `packages/contracts/` (conditional)

**Only if** an audit proves genuine duplication across services/`apps/web`
(e.g. shared TS types or a Python contract). If nothing is proven, this phase is
skipped and documented as such. No new frameworks.

---

## Phase 5 — Docs, DX, tooling consistency

| Item | Action |
|---|---|
| docs reorg | `docs/{architecture,services,development,operations,api}`; fix stale links `/k8s/`, `/terraform/`, `helm/**`, `frontend/src/…` |
| per-service Makefiles | uniform `install/dev/lint/typecheck/test/build`; root `Makefile` orchestrates (no duplicated per-service lines) |
| root config | `.gitignore`, root `pyproject.toml` tool config aligned |
| CI prose | remove last stale service traces |
| FOLLOWUPS | log unrelated pre-existing bugs (below) — **not fixed** |

### Pre-existing issues to log in `docs/migration/FOLLOWUPS.md` (not fixed)

- `services/analysis` coverage `source = ["app","workers"]` and isort
  `known_first_party` list `workers`, but no top-level `workers/` exists.
- `analysis`/`ai` list dev deps in both `[project.optional-dependencies]` and
  `[dependency-groups]`.
- black/isort/mypy already fail on base commit (see `BASELINE.md` §5).
- stray tracked artifacts: `frontend/public/Screenshot 2026-05-25 212539.png`,
  `services/ai/tests/res/*.json`, `services/analysis/test.db`.

---

## Rollback

- Every move is a dedicated pure-rename commit (`git mv`), so the diff is a
  rename with no content change and reverts cleanly.
- Content edits are separate commits per concern, so a bad edit reverts without
  undoing the move.
- Deleting Phases 0.5 / 1 / 2 by commit restores the exact baseline captured in
  `BASELINE.md`.
- No push, no `terraform apply`, no production access at any point.

## Open confirmation before Phase 0.5 executes

1. Approve this MAP (paths + reference set).
2. Approve the Phase 0.5 removal list, including the KEEP list in §0.5d.
