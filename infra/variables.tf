# -----------------------------------------------------------------------------
# General Variables
# -----------------------------------------------------------------------------

variable "project_name" {
  description = "The project name used for resource naming"
  type        = string
  default     = "certgenie"
}

variable "environment" {
  description = "Deployment environment label"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "extra_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# Networking Variables
# -----------------------------------------------------------------------------

variable "vnet_address_space" {
  description = "Address space for the Virtual Network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "container_apps_subnet_prefix" {
  description = "Address prefix for the Container Apps subnet (minimum /23)"
  type        = list(string)
  default     = ["10.0.0.0/23"]
}

# -----------------------------------------------------------------------------
# CosmosDB Variables
# -----------------------------------------------------------------------------

variable "cosmos_database_name" {
  description = "Name of the CosmosDB SQL database"
  type        = string
  default     = "certification-genie"
}

# -----------------------------------------------------------------------------
# Container App Variables
# -----------------------------------------------------------------------------

variable "container_image_tag" {
  description = "Tag of the container image to deploy"
  type        = string
  default     = "latest"
}

variable "app_target_port" {
  description = "Port the application container listens on"
  type        = number
  default     = 8000
}

variable "app_cpu" {
  description = "CPU cores allocated to the container"
  type        = number
  default     = 0.25
}

variable "app_memory" {
  description = "Memory allocated to the container"
  type        = string
  default     = "0.5Gi"
}

variable "app_max_replicas" {
  description = "Maximum number of container replicas for autoscaling"
  type        = number
  default     = 5
}

# -----------------------------------------------------------------------------
# Application Secrets (passed as Container App secrets)
# -----------------------------------------------------------------------------

variable "telegram_bot_token" {
  description = "Telegram Bot API token (bot_id:auth_token)"
  type        = string
  sensitive   = true
}

variable "telegram_webhook_secret" {
  description = "Secret token for Telegram webhook signature verification"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM agents"
  type        = string
  sensitive   = true
}
