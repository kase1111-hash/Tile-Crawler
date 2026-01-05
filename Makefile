.PHONY: help build up down logs clean test dev backend-shell frontend-shell

# Default target
help:
	@echo "Tile-Crawler - Available Commands:"
	@echo ""
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - View service logs"
	@echo "  make clean        - Remove containers, images, and volumes"
	@echo "  make test         - Run backend tests"
	@echo "  make dev          - Start development environment"
	@echo "  make backend-shell  - Open shell in backend container"
	@echo "  make frontend-shell - Open shell in frontend container"

# Build Docker images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d

# Start with logs
up-logs:
	docker-compose up

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# View backend logs
logs-backend:
	docker-compose logs -f backend

# View frontend logs
logs-frontend:
	docker-compose logs -f frontend

# Clean up everything
clean:
	docker-compose down -v --rmi local
	docker system prune -f

# Run tests
test:
	cd backend && python -m pytest tests/ -v

# Development mode with hot-reload
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Open shell in backend container
backend-shell:
	docker-compose exec backend /bin/bash

# Open shell in frontend container
frontend-shell:
	docker-compose exec frontend /bin/sh

# Rebuild and restart a specific service
rebuild-backend:
	docker-compose up -d --build backend

rebuild-frontend:
	docker-compose up -d --build frontend

# Check service status
status:
	docker-compose ps

# Pull latest images
pull:
	docker-compose pull
