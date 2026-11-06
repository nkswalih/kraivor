# Developer entry points for the ai service.
#
# The target set is identical across services/{auth,core,analysis,ai} so the
# root Makefile can orchestrate them with one recursive rule per aggregate.
# Commands mirror .github/workflows/ci.yml: ruff, bandit, pip-audit and pytest
# are hard gates; black, isort and mypy are ::warning:: steps there, so
# `typecheck` and `format` report without failing a build.
#
# `format` is the CI-equivalent check. Use `format-fix` to rewrite files.

SERVICE := ai
COMPOSE_SERVICE := ai
COMPOSE := docker compose -f ../../docker-compose.dev.yml

.PHONY: help install dev lint typecheck test build security format format-fix coverage check sh clean

help: ## Show this help
	@echo make install     install dependencies [uv sync --locked]
	@echo make dev         run $(SERVICE) via docker-compose.dev.yml
	@echo make lint        ruff check [hard CI gate]
	@echo make typecheck   mypy [advisory in CI]
	@echo make test        pytest with coverage [hard CI gate]
	@echo make build       build the production image
	@echo make security    bandit [hard CI gate] - pip-audit is root-only
	@echo make format      black/isort check [advisory, no writes]
	@echo make format-fix  rewrite files with black + isort
	@echo make coverage    coverage report without the maxfail stop
	@echo make check       lint test security
	@echo make sh          shell into the running dev container
	@echo make clean       remove local caches and reports

install: ## Install dependencies from the lockfile
	uv sync --locked

dev: ## Run this service via the dev compose stack
	$(COMPOSE) up --build $(COMPOSE_SERVICE)

lint: ## Ruff (hard CI gate)
	uv run --locked ruff check .

typecheck: ## MyPy (advisory in CI)
	@echo --- mypy
	@uv run --locked mypy . || echo    WARNING: mypy reported issues - not a CI gate

test: ## pytest with coverage (hard CI gate)
	uv run --locked pytest --tb=short --maxfail=3 --cov \
		--cov-report=term-missing:skip-covered --cov-report=xml --cov-report=html -q
	uv run --locked python ../../scripts/check_coverage.py

build: ## Build the production image
	docker build -f Dockerfile -t kraivor/$(SERVICE):local .

security: ## Bandit (hard CI gate). pip-audit is root-only for ai.
	uv run --locked bandit -r . -x ./tests,./.venv,./migrations --configfile pyproject.toml -ll
	@echo    pip-audit: skipped for ai -- torch is not on PyPI - run make security-ai-audit at the repo root.

format: ## Black/isort check (advisory, no writes)
	@echo --- black --check
	@uv run --locked black --check --diff . || echo    WARNING: black check failed - not a CI gate
	@echo --- isort --check-only
	@uv run --locked isort --check-only --diff . || echo    WARNING: isort check failed - not a CI gate

format-fix: ## Rewrite files with black + isort
	uv run --locked black .
	uv run --locked isort .

coverage: ## Coverage report without the maxfail stop
	uv run --locked pytest --cov --cov-report=term-missing --cov-report=html:htmlcov/

check: lint test security ## All hard gates for this service

sh: ## Shell into the running dev container
	$(COMPOSE) exec $(COMPOSE_SERVICE) sh

clean: ## Remove local caches and reports
	uv run --locked python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.ruff_cache', '.pytest_cache', '.mypy_cache', 'htmlcov')]; [p.unlink() for p in pathlib.Path('.').glob('.coverage*') if p.is_file()]"
