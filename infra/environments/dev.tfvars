# Development Environment Configuration
# All resources use pay-per-use / consumption tiers (no fixed costs)

environment = "dev"
location    = "eastus2"

# Networking
vnet_address_space           = ["10.0.0.0/16"]
container_apps_subnet_prefix = ["10.0.0.0/23"]

# CosmosDB (Serverless — pay-per-request)
cosmos_database_name = "certification-genie"

# Container App (Consumption plan — scales to zero)
container_image_tag = "latest"
app_target_port     = 8000
app_cpu             = 0.25
app_memory          = "0.5Gi"
app_max_replicas    = 3

# Application secrets — set via TF_VAR_* env vars or -var flag
# telegram_bot_token      = "SET_VIA_ENV"
# telegram_webhook_secret = "SET_VIA_ENV"
# openai_api_key          = "SET_VIA_ENV"

extra_tags = {
  cost_center = "development"
}
