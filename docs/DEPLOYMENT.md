# Deployment & Rollback

How a change reaches production, and how to undo it. Read the rollback section
before your first deploy.

## Pipeline

`.github/workflows/deploy.yml` targets a single EC2 host. It is **not** a
blue/green or canary setup: the new code replaces the running containers in
place. A bad deploy is therefore a real outage until it is reverted.

```
push to dev  →  CI (ci.yml)  →  deploy.yml  →  terraform apply  →  docker compose up -d  →  host
```

- `dev` is the default remote branch and the deploy trigger.
- Terraform provisions the EC2 instance, security groups, and networking under
  `infra/`.
- Services run from `docker-compose.yml` on the host.
- `core` and `ai` each run a web container, a worker, and a beat scheduler.

### Environment variables on the host

All configuration comes from environment variables on the EC2 instance. A
deployment that starts a Django service without `SECRET_KEY`,
`INTERNAL_REQUEST_TOKEN`, `JWT_*_KEY_PATH`, or `DATABASE_URL` now **refuses to
boot** with a `RuntimeError` naming the missing settings, rather than starting
half-configured. If a service will not start, read the error before restarting
it — it is naming the exact variable.

## Pre-deploy checklist

1. CI is green on the commit, including the coverage gate. Coverage floors are
   enforced per service in each `pyproject.toml` (`fail_under`); the `ai`
   service floor is deliberately low (13%) because that service is largely
   untested — see the gap noted below rather than trusting it as healthy.
2. Migrations are additive. `deploy.yml` runs `manage.py migrate` as part of the
   deploy; a non-additive migration (rename, drop, not-null on an existing
   column) is **not** safe to roll back with this pipeline and needs a plan.
3. `INTERNAL_REQUEST_TOKEN` is set to the same value on every service that
   participates in the internal channel.

## Rollback

There is no automated rollback. Do it manually, and prefer reverting the commit
over patching files on the host.

### 1. Roll back the code

```bash
ssh <host>
cd /opt/kraivor            # adjust if the checkout lives elsewhere
git fetch origin
git checkout <last-good-sha>   # or: git revert <bad-sha>
docker compose up -d --build
```

Pin an explicit SHA rather than a branch. Checking out `dev` can hand you the
same broken commit you are trying to escape.

### 2. Roll back a migration

Check what the deploy actually applied:

```bash
docker compose exec core python manage.py showmigrations <app>
```

- **Additive only** (new column, new table, new index): rolling the code back
  is enough. Leave the schema in place — the old code ignores it.
- **Destructive** (dropped/renamed column): the old code may fail against the
  new schema. Restore from a snapshot rather than attempting a reverse
  migration on a live database.

```bash
docker compose exec postgres pg_dump -U <user> <db> > /var/backups/kraivor-$(date +%F).sql
```

Take this snapshot **before** any deploy that touches schema.

### 3. Verify

```bash
docker compose ps                      # all services up, none restarting
docker compose logs --tail=100 core    # no tracebacks on boot
curl -fsS http://localhost:8002/api/health/
```

A Django service that refuses to boot will show the missing-settings
`RuntimeError` in its logs. That is the expected failure mode for a missing
secret, not a crash to debug.

## Known gaps

These are unresolved and should be treated as risk, not as "the deploy
succeeded":

- **No automated rollback.** Every rollback is manual.
- **No health-gated deploy.** Containers start without confirming they serve
  traffic, so a boot-time failure surfaces as user-facing downtime.
- **`next@15` is the current major and cannot be fully de-adjudicated without
  `next@16`.** As of this writing `npm audit` is clean at `high` and above
  (`next@15.5.26` plus `overrides` on the transitive `postcss`/`sharp`/`nanoid`),
  but advisories land against `next` continuously, and the durable fix is the
  Next 16 major upgrade. Treat that upgrade as scheduled work.
- **The `ai` service is at ~14% test coverage.** Its CI gate passes because the
  floor is set to reality, not because the service is well tested. Treat AI
  service changes as high-risk and test them manually.
- **`services/ai` cannot be fully audited by `pip-audit` out of the box.** It
  pins CPU-only `torch` from the PyTorch index, which is not on PyPI, so
  `pip-audit` aborts with `Dependency not found on PyPI` rather than reporting
  clean. CI exports the lock and audits it against both indexes.
- **`services/notifications` is an empty scaffold** with no deployable
  entrypoint. If anything expects it to be running, it is not.
