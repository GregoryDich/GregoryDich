output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.worker.name
}

output "capacity_provider_name" {
  description = "ECS capacity provider backed by the GPU ASG."
  value       = aws_ecs_capacity_provider.gpu.name
}

output "autoscaling_group_name" {
  description = "GPU Auto Scaling group name."
  value       = aws_autoscaling_group.gpu.name
}

output "security_group_id" {
  description = "Security group shared by GPU instances and worker tasks."
  value       = aws_security_group.worker.id
}

output "log_group_name" {
  description = "CloudWatch log group of the worker."
  value       = aws_cloudwatch_log_group.worker.name
}
