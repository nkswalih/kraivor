# services/notifications — NOT IMPLEMENTED

**Status: empty scaffold. This service contains no working code.**

Every Python file under `app/` is 0 bytes:

```
app/main.py               0 bytes
app/channels/email.py     0 bytes
app/channels/push.py      0 bytes
app/channels/slack.py     0 bytes
app/events/handlers.py    0 bytes
app/events/subscriber.py  0 bytes
app/routers/__init__.py   0 bytes
```

The project layout was created in `b34b5fe` ("set up complete monorepo folder
structure (KRV-001)") and never filled in. Everything else here — `Dockerfile`,
`Makefile`, `requirements/`, `tox.ini`, `uv.lock`, `.flake8` — is real, which
makes the service *look* implemented during a handoff review. It is not. The
Dockerfile cannot produce a working container because there is no entrypoint.

## Where notifications actually live

The working notification code is in the **core** service, not here:

- `services/core/apps/notifications/` — models, views, selectors, serializers,
  Firebase push, Lambda client, Celery consumer
- `services/core/apps/notifications/tests/` — the test suite

If you were looking for notifications behaviour, that is the code you want.

## Why it was not deleted

Deleting a scaffolded service is a product decision, not a cleanup one. Until
someone confirms this service is abandoned, it is left in place with this
notice so the next reviewer does not trust it.

## Do not trust this service's coverage

`pyproject.toml` declares `fail_under = 90`, but there are no tests and no
statements, so coverage reports **100% of zero statements**. That number is
vacuous, not a pass.

It is also absent from the CI matrix in `.github/workflows/ci.yml`
(`[auth, core, ai, analysis]`), so nothing gates it.

## Decision needed

Pick one before this ships:

1. **Delete it** and keep notifications in `core/apps/notifications`.
2. **Implement it** as the standalone notification microservice the scaffold
   implies — and add it to the CI matrix with a real floor.
3. **Leave it**, and remove its `pyproject.toml` coverage gate so it stops
   reporting a fake 100%.
