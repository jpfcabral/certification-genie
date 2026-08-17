variable "vnet_name" {
  description = "Name of the Virtual Network"
  type        = string
}

variable "location" {
  description = "Azure region for the networking resources"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "vnet_address_space" {
  description = "Address space for the Virtual Network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "container_apps_subnet_name" {
  description = "Name of the subnet for Container Apps"
  type        = string
  default     = "container-apps"
}

variable "container_apps_subnet_prefix" {
  description = "Address prefix for the Container Apps subnet (minimum /23 recommended)"
  type        = list(string)
  default     = ["10.0.0.0/23"]
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
