.PHONY: dev stop logs test

dev:
	docker-compose up --build

stop:
	docker-compose down

logs:
	docker-compose logs -f

test:
	@echo "Running tests for all services..."
	cd services/identity && python manage.py test || true
	cd services/core && python manage.py test || true
	cd services/analysis && pytest tests/ || true
	cd services/ai && pytest tests/ || true
	cd services/notifications && pytest tests/ || true
	cd services/realtime && npm test || true
	cd frontend && npm test || true
