# TuneMorph — Developer shortcuts
# Usage: make <target>

.PHONY: install dev backend frontend docker docker-down test clean

## Install Python dependencies
install:
	python -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt

## Start backend dev server (with hot-reload)
backend:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

## Serve the frontend (requires Python)
frontend:
	python -m http.server 3000 --directory frontend

## Run both backend and frontend in parallel
dev:
	@echo "Starting TuneMorph dev servers..."
	@(make backend &) && make frontend

## Build and start via Docker Compose
docker:
	docker-compose up --build

## Stop Docker containers
docker-down:
	docker-compose down

## Run basic health check against running backend
test:
	curl -s http://localhost:8000/ | python3 -m json.tool

## Remove Python cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete; \
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; \
	echo "Cleaned"
