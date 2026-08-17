terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------

resource "azurerm_resource_group" "this" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Local Values
# -----------------------------------------------------------------------------

locals {
  tags = merge(var.extra_tags, {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  })
}

# -----------------------------------------------------------------------------
# Networking Module
# -----------------------------------------------------------------------------

module "networking" {
  source = "./modules/networking"

  vnet_name           = "${var.project_name}-${var.environment}-vnet"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  vnet_address_space           = var.vnet_address_space
  container_apps_subnet_name   = "container-apps"
  container_apps_subnet_prefix = var.container_apps_subnet_prefix

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Container Registry Module
# -----------------------------------------------------------------------------

module "container_registry" {
  source = "./modules/container_registry"

  registry_name       = replace("${var.project_name}${var.environment}acr", "-", "")
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  tags = local.tags
}

# -----------------------------------------------------------------------------
# CosmosDB Module (Serverless — pay-per-use)
# -----------------------------------------------------------------------------

module "cosmos_db" {
  source = "./modules/cosmos_db"

  account_name        = "${var.project_name}-${var.environment}-cosmos"
  database_name       = var.cosmos_database_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Container Apps Module (Consumption plan — scales to zero)
# -----------------------------------------------------------------------------

module "container_apps" {
  source = "./modules/container_apps"

  environment_name    = "${var.project_name}-${var.environment}-env"
  app_name            = "${var.project_name}-${var.environment}-app"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  subnet_id       = module.networking.container_apps_subnet_id
  container_image = "${module.container_registry.login_server}/${var.project_name}:${var.container_image_tag}"
  target_port     = var.app_target_port
  cpu             = var.app_cpu
  memory          = var.app_memory
  max_replicas    = var.app_max_replicas

  environment_variables = [
    {
      name  = "COSMOS_CONNECTION_STRING"
      value = null
      secret_name = "cosmos-connection-string"
    },
    {
      name  = "TELEGRAM_BOT_TOKEN"
      value = null
      secret_name = "telegram-bot-token"
    },
    {
      name  = "TELEGRAM_WEBHOOK_SECRET"
      value = null
      secret_name = "telegram-webhook-secret"
    },
    {
      name  = "OPENAI_API_KEY"
      value = null
      secret_name = "openai-api-key"
    },
    {
      name  = "ENVIRONMENT"
      value = var.environment
    },
  ]

  secrets = [
    {
      name  = "cosmos-connection-string"
      value = module.cosmos_db.connection_string
    },
    {
      name  = "telegram-bot-token"
      value = var.telegram_bot_token
    },
    {
      name  = "telegram-webhook-secret"
      value = var.telegram_webhook_secret
    },
    {
      name  = "openai-api-key"
      value = var.openai_api_key
    },
    {
      name  = "registry-password"
      value = module.container_registry.admin_password
    },
  ]

  registry_server               = module.container_registry.login_server
  registry_username             = module.container_registry.admin_username
  registry_password_secret_name = "registry-password"

  tags = local.tags
}
