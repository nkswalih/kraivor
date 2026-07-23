COMPOSE = docker compose -f ../../docker-compose.dev.yml
SERVICE = analysis

.PHONY: help install format lint typecheck test coverage check fix sh clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dev dependencies inside container
	$(COMPOSE) exec $(SERVICE) uv sync --group dev

format: ## Auto-format with ruff
	$(COMPOSE) exec $(SERVICE) ruff format app/ tests/

lint: ## Lint with ruff
	$(COMPOSE) exec $(SERVICE) ruff check app/ tests/

typecheck: ## Static type check with mypy
	$(COMPOSE) exec $(SERVICE) mypy app/ --strict

test: ## Run tests with pytest
	$(COMPOSE) exec $(SERVICE) pytest tests/ -v --tb=short $(ARGS)

coverage: ## Run tests with coverage report
	$(COMPOSE) exec $(SERVICE) pytest tests/ --cov=app/ --cov-report=term-missing --cov-report=html:htmlcov/

check: lint typecheck test ## Run all checks

fix: format ## Auto-fix formatting

sh: ## Open a shell in the container
	$(COMPOSE) exec $(SERVICE) /bin/sh

clean: ## Clean build artifacts
	$(COMPOSE) exec $(SERVICE) sh -c "rm -rf .ruff_cache/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage; find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true"
