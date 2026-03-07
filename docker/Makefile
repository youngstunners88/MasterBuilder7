# =============================================================================
# MasterBuilder7 - Docker Makefile
# =============================================================================

.PHONY: help build up down restart logs shell clean dev prod

.DEFAULT_GOAL := help

BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
NC := \033[0m

help:
	@echo "$(BLUE)MasterBuilder7 Docker Commands$(NC)"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

dev: ## Start development environment
	@echo "$(YELLOW)Starting development environment...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build -d
	@echo "$(GREEN)Started! API: http://localhost:8080$(NC)"

dev-down: ## Stop development environment
	docker-compose -f docker-compose.yml -f docker-compose.override.yml down

prod: ## Start production environment
	@echo "$(YELLOW)Starting production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)Production started!$(NC)"

prod-down: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

build: ## Build all images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

ps: ## Show running containers
	docker-compose ps

logs: ## Follow logs from all services
	docker-compose logs -f

logs-%: ## Follow logs from specific service
	docker-compose logs -f $*

shell: ## Open shell in mcp-server
	docker-compose exec mcp-server bash

migrate: ## Run database migrations
	docker-compose exec mcp-server python -m alembic upgrade head

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d masterbuilder7

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

test: ## Run tests
	docker-compose exec mcp-server pytest

clean: ## Stop and remove all containers
	docker-compose down -v --remove-orphans

clean-all: ## Clean everything including images
	docker-compose down -v --remove-orphans --rmi all

status: ## Show container status
	@docker-compose ps
	@docker stats --no-stream
