# Phase 3 — `infra/` stays (verification pass)

**Status:** complete, awaiting approval to start Phase 4.
**Branch:** `chore/monorepo-restructure` (off `dev`, base `c2271a4`).

Phase 3 makes **no `infra/` change of its own** — it is the verification pass the
MAP calls for. Terraform, k8s, `lambda/`, `dev`/`prod` and resource addresses are
untouched; the only `infra/` edits on this whole branch are Phase 0.5b's removal
of the two dead services (below), which this pass confirms is complete and
consistent.

## What Phase 0.5b already removed from `infra/`

| File | Δ | What |
|---|---|---|
| `infra/kubernetes/services/notifications/deployment.yaml` | −53 | dead-service manifest |
| `infra/kubernetes/services/realtime/deployment.yaml` | −48 | dead-service manifest |
| `infra/kubernetes/infrastructure/ingress.yaml` | −14 | `/api/notifications` + `/api/realtime` routes |
| `infra/docker/nginx/nginx.dev.conf` | −42 | commented `notifications`/`realtime` upstreams + locations |
| `infra/docker/nginx/nginx.prod.conf` | ±1 | WebSocket comment `(notifications, realtime)` → `(chat, presence — core Channels)` |

No other `infra/` file changed on this branch (`git diff c2271a4..HEAD -- infra/`).

## Verification results

| Check | Result |
|---|---|
| path refs to `frontend/` or `app/` in `infra/**` | **none** — the only `frontend` hits are *deploy names* (`frontend-service`, image `kraivor-frontend`, port 3000), which Phases 1–2 do not change |
| `services/{ai,analysis}/app` refs in `infra/**` | **none** |
| dead-service remnants in `infra/**` | only legitimate ones: the **notifications Lambda** (`infra/lambda/notifications/**`; tf modules `lambda-notifications` + `sqs`), the `notifications` **DB schema** (`postgres/init.sql`), and a nginx feature comment |
| notifications/realtime refs in `docker-compose*.yml` | **none** |
| `./infra/docker/*` compose mounts resolve | **yes** — `postgres/init.sql`, `nginx/nginx.dev.conf`, `nginx/nginx.prod.conf` all exist (`nginx/certs` mount is commented out) |
| every `infra/**/*.yaml` parses (PyYAML, multi-document) | **11 files, 0 failures** (Ingress, Deployments/Services, Namespaces) |
| terraform module `source = "../../modules/*"` targets exist | **yes** — vpc, rds, elasticache, ec2, eks, s3, sqs, lambda-notifications |
| terraform `templatefile("${path.module}/user_data.sh")` exists | **yes** |
| terraform `source_dir = "${path.module}/../../../lambda/notifications"` resolves | **yes** |
| `terraform fmt -check -recursive` + `init -backend=false && validate` | **not run locally** — `terraform` is not installed (unchanged from `BASELINE.md` §1); CI-only, exactly as the MAP states |
| `docker compose -f docker-compose.yml config --quiet` | **exit 0** |
| `docker compose -f docker-compose.dev.yml config --quiet` | **exit 0** |
| `docker compose -f docker-compose.prod.yml config --quiet` | **exit 1** — pre-existing (`FOLLOWUPS.md` F14); file untouched by this branch |

## Correction to the Phase 1 record

Phase 1's write-up claimed `infra/kubernetes/services/frontend/deployment.yaml`
"does not exist". It **does** exist (added in the initial scaffold commit
`b34b5fe`, present at the base commit) and is unchanged on this branch: a
`frontend-service` Deployment/Service using image
`${ECR_REGISTRY}/kraivor-frontend:latest`. It needed no edit because the
`kraivor-frontend` image name is unchanged by the move. The Phase 1 line has been
corrected; the conclusion there (the row needed no work) still holds.

## Commits (nothing pushed)

1. this `PHASE-3.md` (+ the one-line correction in `PHASE-1.md`)

Next: **Phase 4** — `packages/contracts/` (conditional: only if an audit proves
genuine cross-service duplication; otherwise skipped and documented as such).
