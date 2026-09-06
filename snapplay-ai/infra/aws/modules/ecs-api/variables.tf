variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "region" {
  description = "AWS region (awslogs driver)."
  type        = string
}

variable "cluster_name" {
  description = "ECS cluster name (Application Auto Scaling resource id)."
  type        = string
}

variable "cluster_arn" {
  description = "ECS cluster ARN."
  type        = string
}

variable "vpc_id" {
  description = "VPC id."
  type        = string
}

variable "public_subnet_ids" {
  description = "Subnets for the ALB."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Subnets for the Fargate tasks."
  type        = list(string)
}

variable "image" {
  description = "Full API image URI including tag."
  type        = string
}

variable "domain_name" {
  description = "Public hostname served by the ALB."
  type        = string
}

variable "route53_zone_id" {
  description = "Hosted zone for domain_name; empty to skip DNS management."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "Pre-issued certificate ARN; empty to request one (needs route53_zone_id)."
  type        = string
  default     = ""
}

variable "execution_role_arn" {
  description = "Task execution role ARN."
  type        = string
}

variable "task_role_arn" {
  description = "Task role ARN."
  type        = string
}

variable "desired_count" {
  description = "Baseline (minimum) task count."
  type        = number
}

variable "max_count" {
  description = "Upper bound for CPU autoscaling."
  type        = number
}

variable "cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "cpu_target_percent" {
  description = "Average CPU utilisation the target-tracking policy maintains."
  type        = number
  default     = 60
}

variable "environment" {
  description = "Plain environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Environment variables injected from Secrets Manager (name => secret ARN)."
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 14
}

variable "reaper_schedule_expression" {
  description = "EventBridge schedule for the reaper task."
  type        = string
  default     = "rate(5 minutes)"
}
