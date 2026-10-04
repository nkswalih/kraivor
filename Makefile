# Local developer entry points.
#
# These targets mirror .github/workflows/ci.yml deliberately. The previous
# version of this file diverged from CI in four ways, and every one of them
# made a local run look greener than the build would be:
#
#   1. Every command ended in `|| true`, so `make test` and `make lint` exited 0
#      no matter what happened. A failing suite and a passing one were
#      indistinguishable from the exit code.
#   2. The Django services ran `manage.py test` while CI runs `pytest`. The
#      suites are pytest-style, so `manage.py test` was not running the same
#      tests at all -- and it cannot produce the coverage report the gate needs.
#   3. No `--cov`, so the `fail_under` floor in each service's pyproject.toml was
#      never applied locally.
#   4. `bandit` ran with different flags than CI, and `pip-audit` and `isort`
#      were absent, so two hard CI gates had no local equivalent.
#
# Severity is copied from CI rather than invented here. `ruff`, `bandit`,
# `pip-audit` and `pytest` block a merge, so they exit non-zero. `black`,
# `isort` and `mypy` are reported by CI as `::warning::` and do not block, so
# they do not fail a local run either. That way a green `make check` means the
# build will be green.
#
# Each command is spelled out per service rather than generated in a shell
# loop. Make uses `sh` on Linux and `cmd.exe` on Windows, and a `for ... done`
# loop is not portable between the two -- it fails to parse under cmd.exe. One
# line per service works in both. Make stops a target at the first non-zero
# line, which is what the `|| exit 1` in a loop was doing by hand.
#
# The frontend has no `services/` directory, so its gates come from the
# package.json scripts (`typecheck`, `test`, `build`). CI has no separate lint
# step because `next build` runs ESLint as a gate -- typecheck and vitest both
# pass with lint errors present.
#
# Note for `auth`: CI generates `.keys/jwt-{private,public}.pem` before running
# tests. On a fresh clone, generate them once or the JWT tests will not run:
#
#   mkdir -p services/auth/.keys && cd services/auth/.keys
#   openssl genrsa -out jwt-private.pem 2048
#   openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem

.PHONY: dev stop logs check test lint typecheck format security \
        security-ai-audit frontend-check precommit

# isort and black read whole files, and this codebase uses box-drawing and
# arrow characters (->, U+2500) in comments and docstrings. On Windows the
# default encoding is the console codepage, which cannot encode them: the tools
# abort with "Unable to parse file ... 'charmap' codec" and then report the very
# file they failed to read as "imports are incorrectly sorted". That is
# hundreds of phantom findings CI never produces.
#
# PYTHONUTF8=1 enables PEP 540 UTF-8 mode, which is what `open()` needs;
# PYTHONIOENCODING would only have fixed stdout and left the file reads broken.
# GNU Make exports both for the recipe itself, so this applies under cmd.exe and
# sh alike.
export PYTHONUTF8 := 1
export PYTHONIOENCODING := utf-8

# `check` promises to run in CI's order, and `lint`/`test` both need a clean
# Python env, so refuse parallel makes rather than let -j reorder the gates.
.NOTPARALLEL:

dev:
	docker-compose up --build

stop:
	docker-compose down

logs:
	docker-compose logs -f

## Everything CI treats as a hard gate, in the order CI runs it.
check: lint test security frontend-check

# ─── Hard gates: these block a merge ──────────────────────────────────────────

test:
	@echo "==> tests: auth"
	cd services/auth && uv run pytest --cov --maxfail=3 -q
	@echo "==> tests: core"
	cd services/core && uv run pytest --cov --maxfail=3 -q
	@echo "==> tests: analysis"
	cd services/analysis && uv run pytest --cov --maxfail=3 -q
	@echo "==> tests: ai"
	cd services/ai && uv run pytest --cov --maxfail=3 -q

lint:
	@echo "==> ruff: auth"
	cd services/auth && uv run ruff check .
	@echo "==> ruff: core"
	cd services/core && uv run ruff check .
	@echo "==> ruff: analysis"
	cd services/analysis && uv run ruff check .
	@echo "==> ruff: ai"
	cd services/ai && uv run ruff check .

security:
	@echo "==> bandit: auth"
	cd services/auth && uv run bandit -r . -x ./tests,./.venv,./migrations --configfile pyproject.toml -ll
	@echo "==> bandit: core"
	cd services/core && uv run bandit -r . -x ./tests,./.venv,./migrations --configfile pyproject.toml -ll
	@echo "==> bandit: analysis"
	cd services/analysis && uv run bandit -r . -x ./tests,./.venv,./migrations --configfile pyproject.toml -ll
	@echo "==> bandit: ai"
	cd services/ai && uv run bandit -r . -x ./tests,./.venv,./migrations --configfile pyproject.toml -ll
	@echo "==> pip-audit: auth"
	cd services/auth && uv run pip-audit --strict --progress-spinner off
	@echo "==> pip-audit: core"
	cd services/core && uv run pip-audit --strict --progress-spinner off
	@echo "==> pip-audit: analysis"
	cd services/analysis && uv run pip-audit --strict --progress-spinner off
	@echo "==> pip-audit: ai -- SKIPPED, see note below"
	@echo "   CI audits ai with a torch-stripped requirements file; run 'make security-ai-audit' if you have bash."

frontend-check:
	@echo "==> frontend: typecheck"
	cd frontend && npm run typecheck
	@echo "==> frontend: unit tests"
	cd frontend && npm test
	@echo "==> frontend: production build (also gates ESLint)"
	cd frontend && npm run build

# `ai` is excluded from the plain pip-audit above, deliberately, and so it is in
# CI. `ai` pins CPU-only torch from the PyTorch wheel index, which PyPI does not
# carry, so `pip-audit` cannot resolve it and aborts with "Dependency not found
# on PyPI" instead of reporting anything. Running it anyway produces a red
# `make security` that says nothing about vulnerabilities.
#
# CI's workaround exports the lock to a requirements file, strips torch, and
# audits the remainder. That needs bash (a heredoc and /tmp), so it does not
# live in `security` -- this Makefile also runs under cmd.exe on Windows.
#
# `--disable-pip` is load-bearing, not a convenience: pyproject.toml overrides
# argostranslate's pin to `stanza==1.12.2` (GHSA-v5jw-96jm-7h2c,
# CVE-2026-54499), which pip's resolver would refuse. `--no-deps` loses no
# coverage because the export is already fully pinned.
#
# Run this only from a POSIX shell. CI runs it on every push regardless.
security-ai-audit:
	cd services/ai && uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/req.txt
	@python -c "import re,sys; \
	src=open('/tmp/req.txt',encoding='utf-8').read(); \
	out=re.sub(r'(?m)^torch.*\n(?:[ \t].*\n)*','',src); \
	open('/tmp/req-no-torch.txt','w',encoding='utf-8').write(out)"
	cd services/ai && uv run pip-audit --strict --progress-spinner off \
		--no-deps --disable-pip \
		-r /tmp/req-no-torch.txt

# ─── Reported, not gating: mirrors the ::warning:: steps in CI ────────────────
#
# The leading `-` tells make to keep going after a failure, so one service's
# noise does not hide the other three. The commands still exit 0.
#
# CI runs `uv run mypy .` verbatim and I have matched it rather than "fixing"
# it, with one Windows-only caveat worth knowing before you trust the output:
# on Windows `mypy .` in services/auth aborts with "Source file found twice
# under different module names: logging_utils and auth.logging_utils" and stops
# after 1 error, because of how it resolves paths relative to the working
# directory. On Linux it reports the full set. So auth's real findings are
# invisible locally until that is addressed -- it is a module-resolution
# problem, not 1 error. Run `uv run mypy` (no path) to see the actual list.

typecheck:
	-@echo "==> mypy: auth"
	-cd services/auth && uv run mypy . || echo "   WARNING: mypy reported issues in auth (not a CI gate)"
	-@echo "==> mypy: core"
	-cd services/core && uv run mypy . || echo "   WARNING: mypy reported issues in core (not a CI gate)"
	-@echo "==> mypy: analysis"
	-cd services/analysis && uv run mypy . || echo "   WARNING: mypy reported issues in analysis (not a CI gate)"
	-@echo "==> mypy: ai"
	-cd services/ai && uv run mypy . || echo "   WARNING: mypy reported issues in ai (not a CI gate)"

format:
	-@echo "==> black: auth"
	-cd services/auth && uv run black --check --diff . || echo "   WARNING: black check failed in auth (not a CI gate)"
	-@echo "==> black: core"
	-cd services/core && uv run black --check --diff . || echo "   WARNING: black check failed in core (not a CI gate)"
	-@echo "==> black: analysis"
	-cd services/analysis && uv run black --check --diff . || echo "   WARNING: black check failed in analysis (not a CI gate)"
	-@echo "==> black: ai"
	-cd services/ai && uv run black --check --diff . || echo "   WARNING: black check failed in ai (not a CI gate)"
	-@echo "==> isort: auth"
	-cd services/auth && uv run isort --check-only --diff . || echo "   WARNING: isort check failed in auth (not a CI gate)"
	-@echo "==> isort: core"
	-cd services/core && uv run isort --check-only --diff . || echo "   WARNING: isort check failed in core (not a CI gate)"
	-@echo "==> isort: analysis"
	-cd services/analysis && uv run isort --check-only --diff . || echo "   WARNING: isort check failed in analysis (not a CI gate)"
	-@echo "==> isort: ai"
	-cd services/ai && uv run isort --check-only --diff . || echo "   WARNING: isort check failed in ai (not a CI gate)"

precommit:
	pre-commit run --all-files
