variable "name" {
  description = "Resource name prefix; every role is named <name>-<purpose>."
  type        = string
}

variable "account_id" {
  description = "AWS account id (used to scope IAM ARNs)."
  type        = string
}

variable "bucket_arn" {
  description = "Job asset bucket ARN."
  type        = string
}

variable "job_prefix" {
  description = "Key prefix inside the bucket that tasks may touch (contract §10)."
  type        = string
  default     = "jobs/"
}

variable "job_queue_arn" {
  description = "SQS job queue ARN."
  type        = string
}

variable "dlq_arn" {
  description = "SQS dead-letter queue ARN."
  type        = string
}

variable "api_secret_arns" {
  description = "Secrets Manager ARNs the API execution role may read."
  type        = list(string)
}

variable "worker_secret_arns" {
  description = "Secrets Manager ARNs the worker execution role may read."
  type        = list(string)
}

variable "github_repository" {
  description = "owner/name of the GitHub repository allowed to assume the deploy role."
  type        = string
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub OIDC provider (false reuses the account's existing one)."
  type        = bool
  default     = true
}
