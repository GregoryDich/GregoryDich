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

variable "alarm_phone" {
  description = "Optional phone number (E.164, e.g. +14155550123) that receives every alarm and budget notification by SMS. Empty disables the subscription."
  type        = string
  default     = ""

  validation {
    condition     = var.alarm_phone == "" || can(regex("^\\+[1-9][0-9]{6,14}$", var.alarm_phone))
    error_message = "alarm_phone must be empty or an E.164 number: a plus sign followed by 7 to 15 digits, no spaces."
  }
}

variable "api_log_group_name" {
  description = "CloudWatch log group of the API tasks (JSON lines from app.main.JsonFormatter; the reaper writes plain text to the same group)."
  type        = string
}

variable "worker_log_group_name" {
  description = "CloudWatch log group of the GPU worker tasks (plain-text lines from worker.aws_worker)."
  type        = string
}

variable "job_failure_rate_threshold_percent" {
  description = "Alarm when failed jobs reach this share of submitted jobs over 15 minutes."
  type        = number
  default     = 10
}

variable "job_failure_rate_min_jobs" {
  description = "The failure-rate alarm ignores 15-minute windows with fewer submitted jobs than this."
  type        = number
  default     = 20
}

variable "api_error_count_threshold" {
  description = "Alarm when the API logs at least this many ERROR lines in 5 minutes."
  type        = number
  default     = 10
}
