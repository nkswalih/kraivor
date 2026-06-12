.PHONY: help install format lint typecheck security test coverage check fix clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	pip install -r requirements/dev.txt

format: ## Auto-format code with black and isort
	black app/ tests/
	isort app/ tests/

lint: ## Lint code with flake8
	flake8 app/ tests/ --config=.flake8

typecheck: ## Run mypy static type checking
	mypy app/ --strict

security: ## Run security scans with bandit
	bandit -r app/ -x app/tests/

test: ## Run tests with pytest
	pytest tests/ -v --tb=short $(ARGS)

coverage: ## Run tests with coverage report
	pytest tests/ --cov=app/ --cov-report=term-missing --cov-report=html:htmlcov/
	@echo "HTML report: htmlcov/index.html"

check: lint typecheck security test ## Run all checks (lint, typing, security, tests)

fix: format ## Auto-fix all fixable issues (format, lint)

clean: ## Clean build artifacts and caches
	rm -rf .ruff_cache/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage
	rm -rf *.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
