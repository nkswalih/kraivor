# Phase 0 report — Baseline & map

**Status:** complete, awaiting approval before any file moves.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).
**Artifacts:** [`BASELINE.md`](./BASELINE.md), [`MAP.md`](./MAP.md), [`FOLLOWUPS.md`](./FOLLOWUPS.md).

## What was done

1. Created `chore/monorepo-restructure` off `dev`.
2. Ran and recorded the full pre-migration baseline (frontend, 4 Python
   services, all CI gates, Docker images).
3. Inventoried every path-bearing reference the moves will touch and wrote the
   phase-by-phase `MAP.md` with risk + rollback per row.
4. Logged unrelated pre-existing issues in `FOLLOWUPS.md` (nothing fixed).

## Baseline results (all hard gates green pre-migration)

| Area | Result |
|---|---|
| Frontend | lint/typecheck/test/build 0 — **588 tests**, 17 routes |
| auth | **422 passed**, 88.59% (floor 88) |
| core | **831 passed**, 5 skipped, 58.25% (floor 55) |
| analysis | **750 passed**, 72.50% (floor 64) |
| ai | **383 passed**, 29.67% (floor 27) |
| ruff / bandit / pip-audit(3) / coverage(4) / base-images / compose config | all 0 |
| Docker frontend image | built 0 |
| Docker service images | auth/core/analysis/ai all built **0** (5/5 images green) |
| black / isort / mypy | **already failing** on base commit (non-gating `::warning::`) |

`terraform` and `make` are not installed in this environment; those gates are
recorded as "unverified locally" with the exact command to run in CI.

## Key facts confirmed this phase

- Removal scope is small and isolated: **19 tracked files** in
  `services/notifications`, **7** in `services/realtime`; no CI matrix, no
  compose service references them.
- KEEP list for `notifications`-named infrastructure (SQS queue, Lambda) is
  explicit in `MAP.md` §0.5d.
- `docker-compose.prod.yml` does not build the frontend (Vercel hosts it).
- Phase 2 import rewrite is bounded: analysis `app`→`analysis` in **147 files**
  (606 refs), ai `app`→`ai` in **140 files** (595 refs).
- Dockerfiles already carry `ENV PYTHONPATH=/app` and a uvicorn CMD, so Phase 2
  edits those values rather than adding them.

## Gate outcome for this phase

Baseline itself is the gate; nothing has changed yet (`git status`: only the
three docs under `docs/migration/` are new). No moves, no deletions performed.

## STOP — needs your approval

Before I start **Phase 0.5 (remove dead services)** I need a go on:

1. `MAP.md` — the target paths and the full reference set.
2. `MAP.md` §0.5 — the deletion list **and** the KEEP list (§0.5d).

Say "approved" (or point out changes), and I'll execute Phase 0.5, run its gate
checks, and stop again before Phase 1.
