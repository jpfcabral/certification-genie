variable "account_name" {
  description = "Name of the CosmosDB account"
  type        = string
}

variable "database_name" {
  description = "Name of the CosmosDB SQL database"
  type        = string
  default     = "certification-genie"
}

variable "location" {
  description = "Azure region for the CosmosDB account"
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
