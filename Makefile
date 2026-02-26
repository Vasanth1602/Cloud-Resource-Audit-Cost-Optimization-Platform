.PHONY: dev down build test lint migrate seed scan clean logs help

COMPOSE = docker compose -f infra/docker-compose.yml
BACKEND = docker compose -f infra/docker-compose.yml exec backend

help:
	@echo ""
	@echo "  Cloud Governance Platform — Developer Commands"
	@echo "  ─────────────────────────────────────────────"
	@echo "  make dev       Start full local stack (postgres + backend + frontend)"
	@echo "  make down      Stop all services"
	@echo "  make build     Rebuild all Docker images"
	@echo "  make test      Run backend test suite"
	@echo "  make test-cov  Run tests with coverage report"
	@echo "  make lint      Run linters (black, isort, flake8)"
	@echo "  make migrate   Apply Alembic database migrations"
	@echo "  make seed      Seed database with mock data"
	@echo "  make scan      Trigger a mock scan via API"
	@echo "  make logs      Tail all service logs"
	@echo "  make clean     Remove containers, volumes, and caches"
	@echo ""

dev:
	$(COMPOSE) up --build -d
	@echo ""
	@echo "  ✅ Stack is up"
	@echo "  Backend  → http://localhost:8000"
	@echo "  API Docs → http://localhost:8000/docs"
	@echo "  Frontend → http://localhost:3000"
	@echo ""

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build --no-cache

test:
	$(COMPOSE) run --rm backend pytest tests/ -v --tb=short

test-cov:
	$(COMPOSE) run --rm backend pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	$(COMPOSE) run --rm backend black app/ tests/ --check
	$(COMPOSE) run --rm backend isort app/ tests/ --check-only
	$(COMPOSE) run --rm backend flake8 app/ tests/ --max-line-length=100

migrate:
	$(COMPOSE) run --rm backend alembic upgrade head

seed:
	$(COMPOSE) run --rm backend python scripts/seed_db.py

scan:
	@curl -s -X POST http://localhost:8000/api/v1/scans \
		-H "Content-Type: application/json" \
		-d '{"regions": ["us-east-1", "us-west-2"]}' | python -m json.tool

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

clean:
	$(COMPOSE) down -v --remove-orphans
	docker system prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
