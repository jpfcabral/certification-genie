variable "registry_name" {
  description = "Name of the Azure Container Registry (must be globally unique, alphanumeric)"
  type        = string
}

variable "location" {
  description = "Azure region for the Container Registry"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
