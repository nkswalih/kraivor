# Phase 1 — `frontend/` → `apps/web/` + pnpm workspace / Turborepo

**Status:** complete, awaiting approval to start Phase 2.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).

Phase 1 moved the frontend to `apps/web/`, converted it to a root pnpm workspace
run by Turborepo, and repointed every build/reference to the new layout. No app
source was changed — the three Phase-1 commits touch structure and tooling only.

## 1a — Pure rename (separate commit)

`git mv frontend apps/web` — **commit `6310937`**, 443 files, 0 insertions /
0 deletions (rename-only). Committed as a pure rename *before* any content edits
so reviewers can collapse it away.

## 1b — pnpm workspace + Turborepo (content; commit A)

| Item | Before | After |
|---|---|---|
| lockfile | `apps/web/package-lock.json` | root `pnpm-lock.yaml` (package-lock deleted) |
| workspace | none | `pnpm-workspace.yaml` — members `apps/*`, `packages/*` only |
| task runner | none | `turbo.json` + root `package.json` scripts → `turbo run …` |
| package manager pin | none | `packageManager: pnpm@9.15.0` (corepack) |
| overrides | `apps/web/package.json` (npm nested form) | root `package.json` `pnpm.overrides` (pnpm `parent>child` string form; pnpm ignores overrides in non-root workspace packages) |
| web image | `COPY package*.json` + `npm ci` / `npm run build` | 3-stage turbo-prune + pnpm (`corepack enable`, `pnpm install --frozen-lockfile`, `pnpm --filter kraivor-frontend build`, runner `--prod`) |

Decisions inside 1b:

- **Image build context.** MAP §1c wrote `context: ./apps/web`, but the pnpm
  workspace keeps one lockfile at the repo root, so the image is built from the
  **repo root** (`context: .`, `dockerfile: apps/web/Dockerfile`), and a root
  `.dockerignore` keeps the context small. `turbo prune kraivor-frontend
  --docker` emits `out/json` (manifests + pruned lockfile) and `out/full`
  (source); confirmed both `pnpm-lock.yaml` and `pnpm-workspace.yaml` land in
  `out/json/`, so `pnpm install --frozen-lockfile` works unchanged in the
  builder and runner. (User-approved; supersedes the MAP table row.)
- **`typescript` moved from `devDependencies` → `dependencies`.** `next start`
  loads `next.config.ts` and needs `typescript` at runtime; the image omits dev
  deps, so Next tried to auto-install it and failed against pnpm's store layout.
  This matches the file's existing precedent: `@next/bundle-analyzer` and
  `@sentry/nextjs` are also prod deps because the runtime config imports them.
- **Runner installs as the runtime user.** `pnpm install --prod` runs as
  `appuser` (`HOME=/home/appuser`) so pnpm's store path matches the runtime
  user — a root-installed store under `appuser` trips `ERR_PNPM_UNEXPECTED_STORE`
  on any later pnpm action. UID 1001 / `appuser` / EXPOSE 3000 preserved.
- **turbo publishes a glibc binary** → `apk add libc6-compat` on the alpine base.
- **`AGENTS.md`** (turbo's auto-maintained agent guidance for *this* turbo
  version) is committed so later agent runs don't churn it.
- **`.turbo/`** (the turbo build cache) added to `.gitignore`.

## 1c — Reference edits (commit B)

Per MAP §1c, plus everything the sweep found beyond the table:

| File | Change |
|---|---|
| `docker-compose.yml` | frontend `build.context` → `.`, `dockerfile` → `apps/web/Dockerfile` (in commit A — the image cannot build without it) |
| `.github/workflows/ci.yml` | `frontend-tests` + `dependency-audit`: `working-directory: apps/web`, `cache: pnpm` + `cache-dependency-path: pnpm-lock.yaml`, `corepack enable` step, `pnpm install --frozen-lockfile` / `pnpm run {typecheck,test,build}`, `pnpm audit --prod` (was `npm audit --omit=dev`), comment `frontend/Dockerfile` → `apps/web/Dockerfile` |
| `.github/workflows/license-check.yml` | `paths`: `apps/web/package.json`, `pnpm-lock.yaml` |
| `.github/dependabot.yml` | directory `"/frontend"` → `"/"` (pnpm workspace root; dependabot manages the workspace packages from the root manifest) |
| `.github/labeler.yml` | `frontend/**/*` → `apps/web/**/*`; `frontend/package*.json` → `apps/web/package.json`, `pnpm-lock.yaml` |
| `CODEOWNERS` | `/frontend/` → `/apps/web/` |
| `.gitignore` | `frontend/coverage/` → `apps/web/coverage/`; `+ .turbo/` |
| `Makefile` | `frontend-check`: `cd apps/web` + pnpm (`typecheck`, `test`, `build`) |
| `scripts/check_base_images.py` | `("frontend",)` → `("apps/web",)` |
| `README.md` | `cd frontend && npm test` / `npm run test:coverage` → `apps/web` + pnpm |
| `CONTRIBUTING.md` | setup `cd apps/web` + `pnpm install`; gate list `pnpm run typecheck / pnpm test / pnpm run build`; concurrency + testing snippets |
| `docs/ARCHITECTURE.md` | `frontend/src/…` → `apps/web/src/…` (2 rows) |
| `docs/chat/CHAT_SERVICE.md`, `docs/chat/CHAT_V2_ARCHITECTURE.md` | `frontend/src/…` → `apps/web/src/…` (folder trees + file tables) |

Notes on the sweep:

- `infra/kubernetes/services/frontend/deployment.yaml` (MAP row) **does not
  exist** — no k8s manifest deploys the frontend (compose + Vercel). Row was moot.
- `docker-compose.dev.yml` (comment only) and `docker-compose.prod.yml`
  (Vercel-hosted, no build) — unchanged, as MAP predicted.
- `docs/handbook/` and `docs/documents/` are **gitignored local files**
  (`.gitignore:139–140`), not tracked — a `npm → pnpm`/`frontend → apps/web`
  pass was applied to the local copies anyway so local docs stay accurate, but
  nothing there is part of any commit.
- Intentional `frontend` refs kept (per prior KEEP list): all `docs/migration/*`,
  `docs/CODEQL-TRIAGE.md`, and the analysis-service framework detector + tests
  (they detect `frontend/…` conventions in *repos being analyzed*, not this
  repo's layout), the auth test's `testfrontend` hostname, and a prose comment
  in `apps/web/src/types/domain/analysis.ts`.

## Gates (MAP §1d)

| Gate | Result |
|---|---|
| `pnpm install --frozen-lockfile` (root) | **exit 0** |
| `turbo run typecheck` | **exit 0** |
| `turbo run lint` | **exit 0** (warnings only) |
| `turbo run test` | **588 passed / 38 files** — identical to BASELINE |
| `turbo run build` | **exit 0** |
| `docker build -f apps/web/Dockerfile .` | **exit 0** (turbo prune + pnpm, alpine) |
| image smoke run | container **Up**, `GET /` → **HTTP 200** (71 KB) — baseline only built the image; this exceeds it |
| `docker compose -f docker-compose.yml config --quiet` | **exit 0** |
| `python scripts/check_base_images.py` | **exit 0** — digest-pinned, Python floor ≥3.14 |
| grep sweep `frontend/` | none outside the KEEP list |

Route count: the built routes-manifest lists **53 app routes** (15 static + 38
dynamic). MAP's "17 routes" was already superseded in the baseline summary —
source is untouched, so the route set is unchanged (see `FOLLOWUPS.md`).

## Follow-ups / observations

- Smoke run logs show `DOMMatrix is not defined` SSR noise on some reactors/
  knowledge routes — `react-pdf`'s renderer is not Node-safe server-side. This
  is app-level runtime behavior, independent of pnpm vs npm, and only visible
  because the image actually runs now (the baseline never started it). Not a
  migration regression; recorded rather than fixed.
- `apps/web/.dockerignore` is now inert (the root `.dockerignore` governs the
  build). Left in place; candidate for Phase 5 cleanup.
- `terraform`/`make` not installed locally — terraform gate stays CI-only
  (unchanged from baseline).

## Commits (nothing pushed)

1. `6310937` — 1a pure rename (previous session)
2. commit A — root workspace/tooling (package.json, pnpm-workspace.yaml,
   turbo.json, pnpm-lock.yaml, AGENTS.md, .dockerignore, .gitignore, apps/web/
   package.json + Dockerfile, apps/web/package-lock.json deletion, docker-compose.yml)
3. commit B — reference edits (`.github/*`, `CODEOWNERS`, `Makefile`,
   `scripts/check_base_images.py`, `README.md`, `CONTRIBUTING.md`, `docs/…`)
4. commit C — this `PHASE-1.md`

Next: **Phase 2** — Python services (`core → analysis → ai → auth`), each a
pure-rename commit then content edits.