variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "job_queue_name" {
  description = "SQS job queue name."
  type        = string
}

variable "dlq_name" {
  description = "SQS dead-letter queue name."
  type        = string
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix (the LoadBalancer CloudWatch dimension)."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget for the whole account in USD."
  type        = number
}

variable "alarm_email" {
  description = "Optional e-mail subscription for the alarm topic."
  type        = string
  default     = ""
}

variable "queue_age_threshold_seconds" {
  description = "Alarm when the oldest queued job is older than this."
  type        = number
  default     = 600
}

variable "alb_5xx_rate_threshold_percent" {
  description = "Alarm when the 5xx share of ALB requests exceeds this percentage."
  type        = number
  default     = 5
}

variable "require_alarm_email" {
  description = "Fail the plan when alarm_email is empty (true for production environments)."
  type        = bool
  default     = false
}

variable "account_id" {
  description = "AWS account id (trust condition of the budget action role)."
  type        = string
}

variable "job_queue_arn" {
  description = "SQS job queue ARN; the budget kill switch denies sqs:SendMessage on it."
  type        = string
}

variable "api_task_role_name" {
  description = "Name of the API task role the budget kill-switch policy is attached to."
  type        = string
}

variable "api_task_role_arn" {
  description = "ARN of the API task role (scope of the budget action's IAM permission)."
  type        = string
}
