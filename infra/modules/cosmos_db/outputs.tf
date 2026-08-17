output "account_id" {
  description = "The ID of the CosmosDB account"
  value       = azurerm_cosmosdb_account.this.id
}

output "account_name" {
  description = "The name of the CosmosDB account"
  value       = azurerm_cosmosdb_account.this.name
}

output "endpoint" {
  description = "The endpoint of the CosmosDB account"
  value       = azurerm_cosmosdb_account.this.endpoint
}

output "primary_key" {
  description = "The primary key of the CosmosDB account"
  value       = azurerm_cosmosdb_account.this.primary_key
  sensitive   = true
}

output "connection_string" {
  description = "The primary connection string of the CosmosDB account"
  value       = azurerm_cosmosdb_account.this.primary_sql_connection_string
  sensitive   = true
}

output "database_name" {
  description = "The name of the SQL database"
  value       = azurerm_cosmosdb_sql_database.this.name
}
