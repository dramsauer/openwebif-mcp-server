SHELL := /bin/sh

COMPOSE ?= docker compose
PYTHON ?= python3
PYCACHE_PREFIX ?= /private/tmp/openwebif-mcp-pycache
MCP_URL ?= http://localhost:8000/mcp

.DEFAULT_GOAL := help

.PHONY: help init build up start down stop restart logs ps config check test-e2e test-e2e-direct test-e2e-mcp test-e2e-mutation-smoke clean

help: ## Show available targets.
	@awk 'BEGIN {FS = ":.*##"; printf "OpenWebif MCP targets:\n\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init: ## Create .env from .env.example if it does not exist yet.
	@if [ -f .env ]; then \
		echo ".env already exists"; \
	else \
		cp .env.example .env; \
		echo "Created .env. Edit OPENWEBIF_BASE_URL before starting."; \
	fi

build: ## Build the Docker image.
	$(COMPOSE) build

up: ## Start the MCP server in the foreground.
	$(COMPOSE) up --build

start: ## Start the MCP server in the background.
	$(COMPOSE) up --build -d
	@echo "MCP endpoint: $(MCP_URL)"

down: ## Stop and remove the Compose containers.
	$(COMPOSE) down

stop: down ## Alias for down.

restart: down start ## Restart the MCP server in the background.

logs: ## Follow service logs.
	$(COMPOSE) logs -f openwebif-mcp

ps: ## Show Compose service status.
	$(COMPOSE) ps

config: ## Render and validate the Compose configuration.
	$(COMPOSE) config

check: ## Run local syntax and Compose configuration checks.
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) $(PYTHON) -m compileall src tests
	$(COMPOSE) config >/dev/null

test-e2e: build ## Run direct OpenWebif and MCP end-to-end tests.
	$(COMPOSE) run --rm openwebif-mcp python -m tests.e2e_openwebif_mcp

test-e2e-direct: build ## Run only direct OpenWebif API tests.
	$(COMPOSE) run --rm openwebif-mcp python -m tests.e2e_openwebif_mcp --skip-mcp

test-e2e-mcp: build ## Run only MCP HTTP end-to-end tests.
	$(COMPOSE) run --rm openwebif-mcp python -m tests.e2e_openwebif_mcp --skip-direct

test-e2e-mutation-smoke: build ## Run MCP tests and show a short receiver message.
	$(COMPOSE) run --rm -e OPENWEBIF_ALLOW_MUTATIONS=true -e E2E_ALLOW_MUTATION_SMOKE=true openwebif-mcp python -m tests.e2e_openwebif_mcp --skip-direct

clean: ## Remove local Python cache artifacts.
	find src -type d -name __pycache__ -prune -exec rm -rf {} +
