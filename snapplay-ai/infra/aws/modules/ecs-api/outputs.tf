output "alb_dns_name" {
  description = "ALB DNS name."
  value       = aws_lb.this.dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone id (for alias records in other zones)."
  value       = aws_lb.this.zone_id
}

output "alb_arn_suffix" {
  description = "ALB ARN suffix (CloudWatch LoadBalancer dimension)."
  value       = aws_lb.this.arn_suffix
}

output "target_group_arn_suffix" {
  description = "Target group ARN suffix (CloudWatch TargetGroup dimension)."
  value       = aws_lb_target_group.api.arn_suffix
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "task_definition_arn" {
  description = "Latest API task definition ARN."
  value       = aws_ecs_task_definition.api.arn
}

output "security_group_id" {
  description = "Security group of the API tasks."
  value       = aws_security_group.api.id
}

output "log_group_name" {
  description = "CloudWatch log group of the API and reaper tasks."
  value       = aws_cloudwatch_log_group.api.name
}
