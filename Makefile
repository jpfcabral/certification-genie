# ═══════════════════════════════════════════════════════════════════════
# Certification Genie — Makefile
# ═══════════════════════════════════════════════════════════════════════

.PHONY: help dev down build test test-e2e test-fast seed deploy push-image tf-init tf-plan tf-apply tf-output webhook-set webhook-info webhook-delete check-env logs

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

PROJECT_NAME := certgenie
IMAGE_TAG    ?= latest
REGISTRY     ?= $(shell cd infra && terraform output -raw container_registry_login_server 2>/dev/null)

# ─── Help ─────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Local Development ────────────────────────────────────────────────

dev: ## Start local dev (API + Frontend)
	docker compose up --build -d
	@echo ""
	@echo "  Frontend: http://localhost:3000"
	@echo "  API:      http://localhost:8000"
	@echo "  Docs:     http://localhost:8000/docs"

down: ## Stop all containers
	docker compose down

logs: ## Tail API logs
	docker logs -f certification-genie-api

build: ## Build Docker image
	docker build -t $(PROJECT_NAME):$(IMAGE_TAG) .

# ─── Testing ──────────────────────────────────────────────────────────

test: ## Run all tests
	python -m pytest tests/ -q --tb=short

test-e2e: ## Run e2e tests (requires OPENAI_API_KEY)
	python -m pytest tests/e2e/ -v --tb=short

test-fast: ## Run only unit + property tests (no LLM)
	python -m pytest tests/unit/ tests/property/ -q --tb=short

# ─── Seed Data ────────────────────────────────────────────────────────

seed: ## Load seed questions into CosmosDB
	python -m src.seed.loader

# ─── Deploy to Azure ──────────────────────────────────────────────────

tf-init: ## Initialize Terraform
	cd infra && terraform init

tf-plan: ## Plan infrastructure changes
	cd infra && terraform plan \
		-var-file=environments/dev.tfvars \
		-var="telegram_bot_token=$(TELEGRAM_BOT_TOKEN)" \
		-var="telegram_webhook_secret=$(TELEGRAM_WEBHOOK_SECRET)" \
		-var="openai_api_key=$(OPENAI_API_KEY)"

tf-apply: ## Apply infrastructure changes
	cd infra && terraform apply \
		-var-file=environments/dev.tfvars \
		-var="telegram_bot_token=$(TELEGRAM_BOT_TOKEN)" \
		-var="telegram_webhook_secret=$(TELEGRAM_WEBHOOK_SECRET)" \
		-var="openai_api_key=$(OPENAI_API_KEY)" \
		-auto-approve

tf-output: ## Show Terraform outputs
	cd infra && terraform output

push-image: build ## Build and push image to ACR
	@if [ -z "$(REGISTRY)" ]; then echo "ERROR: Run 'make tf-apply' first"; exit 1; fi
	az acr login --name $(shell echo $(REGISTRY) | cut -d. -f1)
	docker tag $(PROJECT_NAME):$(IMAGE_TAG) $(REGISTRY)/$(PROJECT_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(PROJECT_NAME):$(IMAGE_TAG)

deploy: ## Full deploy (push image first, then infra)
	$(MAKE) push-image
	$(MAKE) tf-apply
	@echo ""
	@echo "═══════════════════════════════════════════"
	@echo " Deploy complete!"
	@echo "═══════════════════════════════════════════"
	@cd infra && terraform output container_app_url

# ─── Telegram Webhook ─────────────────────────────────────────────────

webhook-set: ## Set Telegram webhook to Container App URL
	@URL=$$(cd infra && terraform output -raw container_app_url) && \
	curl -s "https://api.telegram.org/bot$(TELEGRAM_BOT_TOKEN)/setWebhook?url=$$URL/webhook&secret_token=$(TELEGRAM_WEBHOOK_SECRET)" | python -m json.tool

webhook-info: ## Get current webhook info
	@curl -s "https://api.telegram.org/bot$(TELEGRAM_BOT_TOKEN)/getWebhookInfo" | python -m json.tool

webhook-delete: ## Delete Telegram webhook
	@curl -s "https://api.telegram.org/bot$(TELEGRAM_BOT_TOKEN)/deleteWebhook" | python -m json.tool

# ─── Utilities ────────────────────────────────────────────────────────

check-env: ## Verify required env vars
	@echo "Checking environment..."
	@test -n "$(TELEGRAM_BOT_TOKEN)" && echo "  ✓ TELEGRAM_BOT_TOKEN" || echo "  ✗ TELEGRAM_BOT_TOKEN"
	@test -n "$(TELEGRAM_WEBHOOK_SECRET)" && echo "  ✓ TELEGRAM_WEBHOOK_SECRET" || echo "  ✗ TELEGRAM_WEBHOOK_SECRET"
	@test -n "$(OPENAI_API_KEY)" && echo "  ✓ OPENAI_API_KEY" || echo "  ✗ OPENAI_API_KEY"
	@echo "  ✓ OPENAI_MODEL = $(or $(OPENAI_MODEL),gpt-5.4-mini)"
