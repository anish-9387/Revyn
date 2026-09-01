# Revyn - developer entry points. Windows users without `make` will find the raw
# equivalents for every target in README.md.

SHELL := /bin/bash
.DEFAULT_GOAL := help

BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/venv
BIN      := $(if $(wildcard $(VENV)/Scripts/python.exe),$(VENV)/Scripts,$(VENV)/bin)
PY       := $(BIN)/python
API      := http://localhost:8000/api/v1

.PHONY: help setup setup-backend setup-frontend seed dev api web test lint format \
        typecheck build cycle metrics up down logs clean

help: ## List the available targets
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sort | awk -F':.*## ' '{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: setup-backend setup-frontend ## Install both toolchains

setup-backend: ## Create the virtualenv and install the API with dev extras
	python -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "$(BACKEND)[dev]"

setup-frontend: ## Install the dashboard dependencies
	cd $(FRONTEND) && npm install --ignore-scripts --no-audit --no-fund

seed: ## Generate the synthetic merchant and fit the recovery model
	cd $(BACKEND) && ../$(PY) -m scripts.seed

dev: ## Run the API and the dashboard together
	$(MAKE) -j2 api web

api: ## Run the API with reload
	cd $(BACKEND) && ../$(BIN)/uvicorn app.main:app --reload --port 8000

web: ## Run the dashboard with reload
	cd $(FRONTEND) && npm run dev

test: ## Run the backend test suite
	cd $(BACKEND) && ../$(PY) -m pytest -q

lint: ## Lint both sides
	cd $(BACKEND) && ../$(BIN)/ruff check app scripts tests
	cd $(FRONTEND) && npm run lint

format: ## Apply safe fixes and formatting to the backend
	cd $(BACKEND) && ../$(BIN)/ruff check --fix app scripts tests && ../$(BIN)/ruff format app scripts tests

typecheck: ## Typecheck the dashboard
	cd $(FRONTEND) && npm run typecheck

build: ## Production build of the dashboard
	cd $(FRONTEND) && npm run build

cycle: ## Drive one full OBSERVE to LEARN cycle against a running API
	curl -fsS -X POST $(API)/ops/cycle | $(PY) -m json.tool

metrics: ## Print the headline recovery numbers from a running API
	curl -fsS $(API)/dashboard/overview | $(PY) -m json.tool

up: ## Start the full stack in Docker (Postgres, Redis, API, dashboard)
	docker compose up --build -d

down: ## Stop the Docker stack and drop its volumes
	docker compose down -v

logs: ## Follow the API logs from the Docker stack
	docker compose logs -f backend

clean: ## Remove build output, caches and the local database
	rm -rf $(FRONTEND)/.next $(FRONTEND)/*.tsbuildinfo
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/revyn.db
	find $(BACKEND) -name __pycache__ -type d -not -path "*/venv/*" -prune -exec rm -rf {} +
