resource "azurerm_container_app_environment" "this" {
  name                = var.environment_name
  location            = var.location
  resource_group_name = var.resource_group_name

  infrastructure_subnet_id = var.subnet_id

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  tags = var.tags
}

resource "azurerm_container_app" "this" {
  name                         = var.app_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  template {
    min_replicas = 0
    max_replicas = var.max_replicas

    container {
      name   = var.app_name
      image  = var.container_image
      cpu    = var.cpu
      memory = var.memory

      dynamic "env" {
        for_each = var.environment_variables
        content {
          name        = env.value.name
          value       = lookup(env.value, "value", null)
          secret_name = lookup(env.value, "secret_name", null)
        }
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.target_port
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  dynamic "secret" {
    for_each = var.secrets
    content {
      name  = secret.value.name
      value = secret.value.value
    }
  }

  dynamic "registry" {
    for_each = var.registry_server != null ? [1] : []
    content {
      server               = var.registry_server
      username             = var.registry_username
      password_secret_name = var.registry_password_secret_name
    }
  }

  tags = var.tags
}
