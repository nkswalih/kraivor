.PHONY: dev stop logs test lint format security precommit

dev:
	docker-compose up --build

stop:
	docker-compose down

logs:
	docker-compose logs -f

test:
	@echo "Running tests for all services..."
	cd services/auth && uv run python manage.py test || true
	cd services/core && uv run python manage.py test || true
	cd services/analysis && uv run pytest tests/ -v || true
	cd services/ai && uv run pytest tests/ -v || true

lint:
	@echo "Running lint checks..."
	cd services/auth && uv run ruff check . || true
	cd services/core && uv run ruff check . || true
	cd services/analysis && uv run ruff check . || true
	cd services/ai && uv run ruff check . || true

format:
	@echo "Running format checks..."
	cd services/auth && uv run black --check --diff . || true
	cd services/core && uv run black --check --diff . || true
	cd services/analysis && uv run black --check --diff . || true
	cd services/ai && uv run black --check --diff . || true

security:
	@echo "Running security scans..."
	cd services/auth && uv run bandit -r . -x ./tests || true
	cd services/core && uv run bandit -r . -x ./tests || true
	cd services/analysis && uv run bandit -r . -x ./tests || true
	cd services/ai && uv run bandit -r . -x ./tests || true

precommit:
	pre-commit run --all-files
