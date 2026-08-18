# -----------------------------------------------------------------------------
# Container App Outputs
# -----------------------------------------------------------------------------

output "container_app_url" {
  description = "The public URL of the Container App"
  value       = module.container_apps.app_url
}

output "container_app_fqdn" {
  description = "The FQDN of the Container App"
  value       = module.container_apps.app_fqdn
}

# -----------------------------------------------------------------------------
# CosmosDB Outputs
# -----------------------------------------------------------------------------

output "cosmosdb_endpoint" {
  description = "The CosmosDB account endpoint"
  value       = module.cosmos_db.endpoint
}

output "cosmosdb_database_name" {
  description = "The CosmosDB database name"
  value       = module.cosmos_db.database_name
}

# -----------------------------------------------------------------------------
# Container Registry Outputs
# -----------------------------------------------------------------------------

output "container_registry_login_server" {
  description = "The Container Registry login server URL"
  value       = module.container_registry.login_server
}

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------

output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.this.name
}

output "container_app_name" {
  description = "The name of the Container App"
  value       = module.container_apps.app_name
}
