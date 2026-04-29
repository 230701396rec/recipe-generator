# Project name used in demo resources.
variable "project_name" {
  description = "Logical project name for Terraform demonstration output."
  type        = string
  default     = "recipe-generator"
}

# Environment label for demonstration only.
variable "environment" {
  description = "Environment label used by demonstration resources."
  type        = string
  default     = "dev"
}

# Name of the generated local demo file.
variable "output_file_name" {
  description = "Filename for the generated local demo artifact."
  type        = string
  default     = "terraform-demo.txt"
}
