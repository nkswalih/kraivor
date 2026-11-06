# Root developer entry points.
#
# Each Python service exposes the same target set in its own Makefile
# (install/dev/lint/typecheck/test/build/security/format/format-fix/coverage/
# check/sh/clean). This file owns only the orchestration: one recursive rule per
# aggregated target, not a block per service. Recursive make is portable under
# both sh and cmd.exe; a shell `for ... done` loop is not.
#
# Hard gates mirror .github/workflows/ci.yml: ruff, bandit, pip-audit and
# pytest exit non-zero. black, isort and mypy are `::warning::` steps in CI, so
# `typecheck` and `format` are advisory and do not fail `check`; `format-fix`
# rewrites files and is opt-in.
#
# Frontend gates come from apps/web's package.json scripts. `frontend-check`
# runs the same three steps as CI's frontend job: typecheck, unit tests, and the
# production build (which also gates ESLint).
#
# UTF-8: isort and black read whole files, and the codebase uses box-drawing
# characters. PYTHONUTF8 makes those reads UTF-8 on Windows; without it the
# tools abort and then report the files they could not read as unsorted.

SERVICES := auth core analysis ai
WEB := apps/web

# Aggregated Python targets. The per-service pattern rules are generated below,
# so adding a service is a one-line change to SERVICES.
AGGREGATES := install lint typecheck test build security format format-fix coverage

export PYTHONUTF8 := 1
export PYTHONIOENCODING := utf-8

.PHONY: dev stop logs check test lint typecheck build security format format-fix \
        coverage frontend-check web-install web-dev web-lint web-typecheck \
        web-test web-build web-format security-ai-audit precommit

# `check` promises CI's order, so refuse parallel makes rather than let -j
# reorder the gates.
.NOTPARALLEL:

$(AGGREGATES): %: $(foreach s,$(SERVICES),$(s)-%)
	@:

$(foreach s,$(SERVICES),$(eval $(s)-%: ; $$(MAKE) -C services/$(s) $$*))

install: web-install
build: web-build

# ---- Frontend (single pnpm workspace package) ----

web-install:
	pnpm install --frozen-lockfile

web-dev:
	cd $(WEB) && pnpm dev

web-lint:
	cd $(WEB) && pnpm run lint

web-typecheck:
	cd $(WEB) && pnpm run typecheck

web-test:
	cd $(WEB) && pnpm test

web-build:
	cd $(WEB) && pnpm run build

web-format:
	cd $(WEB) && pnpm run format

frontend-check: web-typecheck web-test web-build

# ---- Compose stack ----

dev:
	docker compose -f docker-compose.dev.yml up --build

stop:
	docker compose -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.dev.yml logs -f

# ---- Aggregate checks ----

check: lint test security frontend-check

# `ai` pins CPU-only torch from the PyTorch wheel index, which PyPI does not
# carry, so pip-audit cannot resolve it. CI exports the lock, strips torch and
# audits the remainder. That needs bash, so it lives here rather than in the
# per-service target.
security-ai-audit:
	cd services/ai && uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/req.txt
	@python -c "import re,sys; \
	src=open('/tmp/req.txt',encoding='utf-8').read(); \
	out=re.sub(r'(?m)^torch.*\n(?:[ \t].*\n)*','',src); \
	open('/tmp/req-no-torch.txt','w',encoding='utf-8').write(out)"
	cd services/ai && uv run pip-audit --strict --progress-spinner off \
		--no-deps --disable-pip \
		-r /tmp/req-no-torch.txt

precommit:
	pre-commit run --all-files
