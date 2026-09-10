output "api_url" {
  description = "Public base URL of the API."
  value       = "https://${var.domain_name}"
}

output "alb_dns_name" {
  description = "DNS name of the application load balancer (CNAME/alias target for domain_name)."
  value       = module.ecs_api.alb_dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster shared by the API service and the GPU worker service."
  value       = aws_ecs_cluster.this.name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs for the api and worker images."
  value       = { for k, r in aws_ecr_repository.this : k => r.repository_url }
}

output "s3_bucket_name" {
  description = "Job asset bucket (S3_BUCKET)."
  value       = module.storage.bucket_name
}

output "cloudfront_domain_name" {
  description = "CloudFront domain for signed asset URLs (empty when CloudFront is disabled)."
  value       = module.storage.cloudfront_domain_name
}

output "sqs_job_queue_url" {
  description = "Job queue URL (SQS_JOB_QUEUE_URL)."
  value       = module.queue.job_queue_url
}

output "sqs_dlq_url" {
  description = "Dead-letter queue URL (SQS_DLQ_URL)."
  value       = module.queue.dlq_url
}

output "github_deploy_role_arn" {
  description = "IAM role assumed by GitHub Actions through OIDC (AWS_DEPLOY_ROLE_ARN repository variable)."
  value       = module.iam.github_deploy_role_arn
}

output "worker_autoscaling_group_name" {
  description = "Auto Scaling group backing the GPU capacity provider."
  value       = module.ecs_gpu_worker.autoscaling_group_name
}

output "secret_arns" {
  description = "Secrets Manager ARNs to populate after the first apply."
  value       = module.secrets.secret_arns
}

output "alarm_topic_arn" {
  description = "SNS topic receiving CloudWatch alarms and budget notifications."
  value       = module.observability.sns_topic_arn
}

output "api_task_definition_arn" {
  description = "Latest API task definition; deploy.yml runs `python -m app.checks` on it as a one-off Fargate task after apply."
  value       = module.ecs_api.task_definition_arn
}

output "api_security_group_id" {
  description = "Security group of the API tasks (for one-off tasks such as the deployment checks)."
  value       = module.ecs_api.security_group_id
}

output "api_log_group_name" {
  description = "CloudWatch log group of the API, reaper and deployment-check tasks."
  value       = module.ecs_api.log_group_name
}

output "private_subnet_ids" {
  description = "Private subnets that ECS tasks run in."
  value       = module.vpc.private_subnet_ids
}

output "budget_action_id" {
  description = "AWS Budgets action that denies job intake at 100 % of the monthly budget; reset it after the incident (see modules/observability)."
  value       = module.observability.budget_action_id
}
