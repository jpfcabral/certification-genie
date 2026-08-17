output "registry_id" {
  description = "The ID of the Container Registry"
  value       = azurerm_container_registry.this.id
}

output "login_server" {
  description = "The login server URL of the Container Registry"
  value       = azurerm_container_registry.this.login_server
}

output "admin_username" {
  description = "The admin username of the Container Registry"
  value       = azurerm_container_registry.this.admin_username
}

output "admin_password" {
  description = "The admin password of the Container Registry"
  value       = azurerm_container_registry.this.admin_password
  sensitive   = true
}
