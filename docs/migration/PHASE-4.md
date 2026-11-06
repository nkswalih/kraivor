# Phase 4 — `packages/contracts/` (conditional): skipped

**Status:** audited; **not justified**; phase skipped per the MAP's own condition.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).
**Code change:** **none** — no package, no dependency, no workspace entry, no
service/web edit.

The MAP makes this phase conditional:

> **Only if** an audit proves genuine duplication across services/`apps/web`
> (e.g. shared TS types or a Python contract). If nothing is proven, this phase
> is skipped and documented as such. No new frameworks.

This document is that audit and that record.

## Method

Evidence only; no imports executed, no runtime needed.

1. **Python surface** — AST-parsed every `*.py` under
   `services/{core,auth,analysis,ai}` (excluding `.venv`/`__pycache__`) and
   extracted class definitions with model-like bases
   (`BaseModel`/`Serializer`/`Schema`/`Model`) plus their annotated fields.
2. **TypeScript surface** — extracted every
   `export interface|type|enum` under `apps/web/src` (excluding
   `node_modules`/`.next`).
3. **File-level duplication** — whitespace-normalised SHA-256 of every
   `.py`/`.ts`/`.tsx` under `services/` and `apps/web/src` (excluding
   `__init__.py` and build dirs) to find byte-identical files across
   boundaries.
4. **Coupling** — precise scan for cross-service private imports and for any
   pre-existing shared package.
5. **Consumers** — workspace layout (`pnpm-workspace.yaml`, root `package.json`).

## Evidence

| Probe | Result |
|---|---|
| TS consumers / workspace shape | `apps/web` is the **only** TS package; `packages/` does not exist; `pnpm-workspace.yaml` already globs `packages/*` |
| model-like Python classes | **315** — core 117, auth 28, analysis 51, ai 119 |
| cross-service class-name collisions | **2** — `HealthResponse`, `JWTPayload` — **both different fields**; **0 identical** |
| identical source files across boundaries | **0** of **1,133** scanned |
| cross-service private imports (`from core/auth/analysis/ai …`) | **0** |
| exported TS declarations in `apps/web` | **269 declarations / 262 unique names** |
| same-name TS declarations | **6** — **1 identical**, **5 different shapes** (see below) |
| TS names that also name a Python class | **38** — the HTTP boundary, not shared code |

### The 2 Python collisions (neither is a shared contract)

| Name | `analysis` | `ai` |
|---|---|---|
| `HealthResponse` | `status, service, version, timestamp, dependencies` | `status, version, service` |
| `JWTPayload` | `sub, email, workspace_ids, roles` | `sub, email, name, workspace_ids, roles` |

Both are independently owned per-service response/auth models whose shapes have
already diverged. Sharing them would save ~6 lines and couple two services.

### The 6 same-name TS declarations

| Name | Verdict |
|---|---|
| `ChatMessage` | different — `types/api` is the snake_case REST DTO (`message_id…deleted_at`); `domain/ai` is the camelCase chat UI model (`id, role, content…`) |
| `SendMessagePayload` | different — REST payload vs AI-session payload (attachments/model/repo_ids/mode) |
| `Workspace` | different — snake_case REST DTO vs camelCase UI model |
| `WorkspaceMember` | different — `user_id/joined_at` vs `userId/joinedAt` |
| `PaginatedResponse` | different — three envelope shapes (`data+meta`, `results+total+page+page_size`, `count+next+previous+results`) |
| `ErrorSuggestedAction` | **identical** union duplicated in `types/domain/ai.ts:1` and `lib/api/ai-api.ts:85` |

The one real duplicate (`ErrorSuggestedAction`) is **inside a single app**; the
fix is a local import, not a workspace package.

## Why no package is justified

Three plausible shapes of `packages/contracts`, each rejected on evidence:

1. **TS-only package.** `apps/web` would be its only consumer. That relocates
   code and adds tsconfig project references/build wiring for **zero**
   cross-package reuse; it does not remove the one real duplicate (a one-line
   import inside `apps/web`).
2. **Python-only package.** There are **zero** identical cross-service
   definitions (probe above). Packaging them would need a uv workspace/path
   dependency and couple services for ~0 saved lines — and cut against the
   ground rule against cross-service imports of private code.
3. **Cross-language package.** The 38 TS↔Python name overlaps are the REST
   boundary. Making them a shared contract requires OpenAPI/JSON-Schema
   **codegen**, i.e. a new framework — explicitly out of scope for this phase.

## What would reopen this phase

- a **second TS consumer** needs the same API types (new app, or `packages/ui`); or
- two services come to exchange a **shared typed payload** (queue/DTO) with
  identical definitions; or
- the team adopts **OpenAPI/JSON-Schema codegen** — then `packages/contracts`
  becomes the generated output and this decision is revisited.

## Findings logged (not fixed, per ground rules)

- **F16** — `analysis` defines `HealthResponse` twice (router-local with
  `dependencies`; `schemas/common.py` without), and the `schemas` export is
  unused by the router. Intra-service, so a contracts package would not address
  it.
- **F17** — `apps/web` hand-maintains TS types that mirror service models (38
  names); nothing generates them, so drift is undetected. Recorded as an
  `info`-severity risk, not a defect.

## Verification

- No code touched: the commit for this phase contains only
  `docs/migration/PHASE-4.md` and two `FOLLOWUPS.md` rows.
- Workspace is unchanged, so `pnpm`/Turborepo and all Phase 1–2 gates are
  unaffected; no re-run required.

Next: **Phase 5** — docs, DX, tooling consistency.
