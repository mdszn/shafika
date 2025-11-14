.PHONY: help build build-% up down logs logs-% shell-% clean restart restart-% ps migrate init scale

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Ethereum Indexer - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make build-block-poller    # Build only block-poller"
	@echo "  make restart-log-processor # Restart only log-processor"
	@echo "  make logs-redis            # View redis logs"
	@echo "  make scale BLOCK=8 LOG=4   # Scale to 8 block & 4 log processors"

# Build all services
build: ## Build all Docker images
	@echo "$(BLUE)Building all services...$(NC)"
	docker-compose build

# Build specific service
build-%: ## Build specific service (e.g., make build-block-poller)
	@echo "$(BLUE)Building $*...$(NC)"
	docker-compose build $*

# Start all services
up: ## Start all services in detached mode
	@echo "$(GREEN)Starting all services...$(NC)"
	docker-compose up -d

# Start specific service
up-%: ## Start specific service (e.g., make up-block-poller)
	@echo "$(GREEN)Starting $*...$(NC)"
	docker-compose up -d $*

# Scale workers (default: 4 block, 2 log processors)
scale: ## Scale worker services (e.g., make scale BLOCK=4 LOG=2)
	@echo "$(GREEN)Scaling workers...$(NC)"
	@echo "  Block Processors: $(or $(BLOCK),4)"
	@echo "  Log Processors: $(or $(LOG),2)"
	docker-compose up -d --scale block-processor=$(or $(BLOCK),4) --scale log-processor=$(or $(LOG),2)
	@echo "$(GREEN)Workers scaled!$(NC)"

# Initialize database (runs automatically on first 'make up')
init: ## Manually initialize database tables
	@echo "$(BLUE)Initializing database...$(NC)"
	docker-compose up db-init
	@echo "$(GREEN)Database initialized!$(NC)"

# Stop all services
down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose down

# Stop specific service
down-%: ## Stop specific service (e.g., make down-block-poller)
	@echo "$(YELLOW)Stopping $*...$(NC)"
	docker-compose stop $*

# View logs for all services
logs: ## View logs for all services
	docker-compose logs -f

# View logs for specific service
logs-%: ## View logs for specific service (e.g., make logs-block-poller)
	docker-compose logs -f $*

# Shell into specific service
shell-%: ## Open shell in specific service (e.g., make shell-block-poller)
	docker-compose exec $* /bin/bash

# Restart all services
restart: down up ## Restart all services

# Restart specific service
restart-%: ## Restart specific service (e.g., make restart-block-poller)
	@echo "$(YELLOW)Restarting $*...$(NC)"
	docker-compose restart $*

# Show service status
ps: ## Show status of all services
	docker-compose ps

# Clean everything
clean: ## Stop and remove all containers, volumes, and images
	@echo "$(YELLOW)Cleaning up...$(NC)"
	docker-compose down -v
	docker system prune -f

# Database migrations
migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	docker-compose exec postgres psql -U postgres -d eth_indexer -f /docker-entrypoint-initdb.d/init.sql

# Initialize database
db-init: ## Initialize database schema
	@echo "$(BLUE)Initializing database...$(NC)"
	docker-compose exec block-processor python -m scripts.run_migration

# Redis CLI
redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

# PostgreSQL CLI
psql: ## Open PostgreSQL CLI
	docker-compose exec postgres psql -U postgres -d eth_indexer

# Development: rebuild and restart specific service
dev-%: build-% restart-% ## Rebuild and restart specific service (e.g., make dev-block-poller)
	@echo "$(GREEN)$* updated and restarted$(NC)"

# Quick development cycle for all services
dev-all: build restart ## Rebuild and restart all services
	@echo "$(GREEN)All services updated$(NC)"

# Check service health
health: ## Check health status of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# View resource usage
stats: ## Show Docker stats for all running containers
	docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

