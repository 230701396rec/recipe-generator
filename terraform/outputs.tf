# Absolute path of the generated local demo file.
output "demo_file_path" {
  description = "Path to the generated demonstration file."
  value       = local_file.demo_info.filename
}

# ID of the null resource to show apply execution.
output "demo_step_id" {
  description = "ID of the demonstration null_resource."
  value       = null_resource.demo_step.id
}
