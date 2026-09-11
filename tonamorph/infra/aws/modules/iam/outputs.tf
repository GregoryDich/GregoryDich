output "api_execution_role_arn" {
  description = "Execution role for the API task definition."
  value       = aws_iam_role.api_execution.arn
}

output "worker_execution_role_arn" {
  description = "Execution role for the worker task definition."
  value       = aws_iam_role.worker_execution.arn
}

output "api_task_role_arn" {
  description = "Task role assumed by the API containers."
  value       = aws_iam_role.api_task.arn
}

output "worker_task_role_arn" {
  description = "Task role assumed by the worker containers."
  value       = aws_iam_role.worker_task.arn
}

output "ecs_instance_profile_name" {
  description = "Instance profile for the GPU capacity provider's EC2 instances."
  value       = aws_iam_instance_profile.ecs_instance.name
}

output "github_deploy_role_arn" {
  description = "Role assumed by GitHub Actions through OIDC."
  value       = aws_iam_role.github_deploy.arn
}

output "api_task_role_name" {
  description = "Name of the API task role (target of the budget kill-switch policy)."
  value       = aws_iam_role.api_task.name
}
