terraform {
  required_version = ">= 1.5.0"

  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Demonstration-only file output (no cloud resources).
resource "local_file" "demo_info" {
  filename = "${path.module}/${var.output_file_name}"
  content  = <<-EOT
    Terraform DevOps Demo
    Project: ${var.project_name}
    Environment: ${var.environment}
  EOT
}

# Demonstration-only triggerable resource.
resource "null_resource" "demo_step" {
  triggers = {
    project     = var.project_name
    environment = var.environment
    timestamp   = timestamp()
  }
}
