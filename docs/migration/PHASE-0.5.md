# Phase 0.5 — Remove dead services

**Status:** complete, awaiting approval to start Phase 1.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).

Both services were non-functional scaffolds in no CI matrix, no compose file, and
no lockstep build. Nothing else was touched.

## Removed

| Path | Tracked files |
|---|---|
| `services/notifications/` | 19 (`git rm -r`) |
| `services/realtime/` | 7 (`git rm -r`) |
| `infra/kubernetes/services/notifications/deployment.yaml` | 1 |
| `infra/kubernetes/services/realtime/deployment.yaml` | 1 |

`infra/kubernetes/infrastructure/ingress.yaml`: removed the `/api/notifications`
and `/ws` routes. Untracked leftovers under the two service directories were
deleted from disk (not part of the commit).

**Kept** per MAP §0.5d: SQS `kraivor-notifications-*` (terraform), the notification
Lambda (`infra/terraform/modules/lambda-notifications/`, `infra/lambda/notifications/`),
`docs/CODEQL-TRIAGE.md`, and every Core notification / Django Channels feature.

## Reference edits

The reference set in MAP §0.5c:

- `scripts/check_base_images.py:196` — `("frontend", "services/realtime")` → `("frontend",)`.
- `scripts/check_coverage.py` — docstring reworded off the removed service.
- `docs/ARCHITECTURE.md`, `README.md`, `docs/DEPLOYMENT.md`, `.github/workflows/ci.yml`.

The grep sweep found more dangling references than §0.5c listed. All are
path/comment/description level — no runtime behaviour:

- `README.md` — Mermaid diagram: dropped the `Notifications` node and the whole
  `Realtime` subgraph; the WebSocket edge is now `FE <-->|/ws/ WebSocket| GW`
  (Django Channels in Core).
- `docs/KRAIVOR_COMPLETE_DOCUMENTATION.md` — §6.5/§6.6 reframed ("served by
  Core"); ASCII diagram column `Notifications :8005` → `Channels (WS)` / `(in Core)`,
  the `Realtime :8006` band → Core Channels; Redis `Socket.io Adapter` → Channels
  layer; Kafka consumers `Core, Realtime` → `Core`; deployment-table rows removed.
- `docs/DOCKER.md` — full-stack list and the Service URLs rows.
- `infra/docker/nginx/nginx.prod.conf` — `/ws/` comment (proxy target is `core`).
- `infra/docker/nginx/nginx.dev.conf` — removed the dead commented
  notifications block and the commented websocket/realtime upstreams.
- `docs/postman/Kraivor Complete API.postman_{collection,environment}.json` — the
  collection documented a standalone "Notification Service" (`:8005`) that never
  functioned. Repointed to Core (`:8002`), which actually serves
  `/api/notifications/`, `.../unread_count/`, `.../<pk>/read/`, etc.; renamed the
  folder to "Notifications (Core)"; dropped the `notificationsBaseUrl` variable
  and the unsupported `read-all` / `preferences` endpoints; fixed the description.

## Gates (MAP §0.5e)

| Gate | Result |
|---|---|
| `python scripts/check_base_images.py` | **exit 0** |
| `python scripts/check_coverage.py` in `auth` | **exit 0** — 88.59% (floor 88%) |
| `python scripts/check_coverage.py` in `core` | **exit 0** — 58.25% (floor 55%) |
| `python scripts/check_coverage.py` in `analysis` | **exit 0** — 72.50% (floor 64%) |
| `python scripts/check_coverage.py` in `ai` | **exit 0** — 29.67% (floor 27%) |
| `docker compose -f docker-compose.yml config --quiet` | **exit 0** |
| grep sweep for `services/notifications`, `services/realtime`, `notifications-service`, `realtime-service` | **none outside the KEEP list** |

Extra checks: YAML parse of `ci.yml` + `ingress.yaml`, `ruff` + `py_compile` on the
two edited scripts, JSON parse of both Postman files — all green. Coverage numbers
are identical to the frozen `BASELINE.md`.

`terraform`/`make` are not installed locally, so the terraform gate stays CI-only
(unchanged from baseline). `docker-compose.prod.yml` cannot be `config`-validated
in isolation or layered on the base because it profiles base infra as `removed`
(`FOLLOWUPS.md` F14) — pre-existing, not caused by this phase.

## Notes

- No push. No `terraform apply`. No change outside the Phase 0.5 scope.
- Next: **Phase 1** — `frontend/` → `apps/web/` + pnpm workspace / Turborepo.
