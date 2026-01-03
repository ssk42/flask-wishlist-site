.PHONY: help build up down restart logs shell test clean migrate db-reset

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %%-15s %%s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d
	@echo "Application running at http://localhost:5001"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Show logs from all services
	docker compose logs -f

logs-web: ## Show logs from web service only
	docker compose logs -f web

shell: ## Open shell in web container
	docker compose exec web /bin/bash

shell-db: ## Open PostgreSQL shell
	docker compose exec db psql -U wishlist_user -d wishlist

test: ## Run tests in Docker
	docker compose exec web pytest

test-cov: ## Run tests with coverage report
	docker compose exec web pytest --cov=. --cov-report=html

migrate: ## Run database migrations
	docker compose exec web flask db upgrade

migrate-create: ## Create a new migration
	@read -p "Enter migration message: " msg; \
	docker compose exec web flask db migrate -m "$$msg"

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker compose down -v; \
		docker compose up -d db; \
		sleep 5; \
		docker compose exec db psql -U wishlist_user -d wishlist -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		docker compose up -d web; \
		$(MAKE) migrate; \
	fi

clean: ## Remove containers, volumes, and images
	docker compose down -v --remove-orphans
	docker system prune -f

prod-up: ## Start production-like environment
	docker compose --profile production up -d
	@echo "Production application running at http://localhost:8000"

prod-down: ## Stop production environment
	docker compose --profile production down

dev: up ## Alias for 'up' - start development environment

install-local: ## Install dependencies locally (without Docker)
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run-local: ## Run Flask locally (without Docker)
	. venv/bin/activate && flask run

test-local: ## Run tests locally (without Docker)
	. venv/bin/activate && pytest
