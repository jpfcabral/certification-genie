variable "environment_name" {
  description = "Name of the Container Apps environment"
  type        = string
}

variable "app_name" {
  description = "Name of the Container App"
  type        = string
}

variable "location" {
  description = "Azure region for the Container Apps environment"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the Container Apps environment"
  type        = string
}

variable "container_image" {
  description = "Container image to deploy (e.g., registry.azurecr.io/app:latest)"
  type        = string
}

variable "target_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "CPU allocation for the container (in cores)"
  type        = number
  default     = 0.25
}

variable "memory" {
  description = "Memory allocation for the container (e.g., 0.5Gi)"
  type        = string
  default     = "0.5Gi"
}

variable "max_replicas" {
  description = "Maximum number of replicas for scaling"
  type        = number
  default     = 5
}

variable "environment_variables" {
  description = "List of environment variables for the container"
  type = list(object({
    name        = string
    value       = optional(string)
    secret_name = optional(string)
  }))
  default = []
}

variable "secrets" {
  description = "List of secrets for the Container App"
  type = list(object({
    name  = string
    value = string
  }))
  default   = []
  sensitive = true
}

variable "registry_server" {
  description = "Container registry login server URL"
  type        = string
  default     = null
}

variable "registry_username" {
  description = "Container registry username"
  type        = string
  default     = null
}

variable "registry_password_secret_name" {
  description = "Name of the secret containing the container registry password"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
