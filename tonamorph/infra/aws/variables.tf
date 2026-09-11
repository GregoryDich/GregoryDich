variable "region" {
  description = "AWS region for every regional resource."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project slug used as the prefix of every resource name."
  type        = string
  default     = "tonamorph"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,23}$", var.project_name))
    error_message = "project_name must be 2-24 lowercase letters, digits or hyphens and start with a letter."
  }
}

variable "environment" {
  description = "Deployment environment slug (prod, staging, ...)."
  type        = string
  default     = "prod"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,11}$", var.environment))
    error_message = "environment must be 2-12 lowercase letters or digits."
  }
}

variable "domain_name" {
  description = "Public hostname of the API (the contract's base URL host, e.g. api.tonamorph.com)."
  type        = string
}

variable "route53_zone_id" {
  description = "Hosted zone that owns domain_name. When set, the ACM certificate is DNS-validated and an alias record for the ALB is created automatically."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ARN of an already-issued ACM certificate for domain_name in this region. Required when route53_zone_id is empty."
  type        = string
  default     = ""
}

variable "gpu_instance_type" {
  description = "EC2 instance type for the GPU worker capacity provider (A10G g5.* or T4 g4dn.*)."
  type        = string
  default     = "g5.xlarge"

  validation {
    condition     = can(regex("^(g5|g4dn)\\.[a-z0-9]+$", var.gpu_instance_type))
    error_message = "gpu_instance_type must be a g5.* (A10G) or g4dn.* (T4) instance type."
  }
}

variable "worker_min_capacity" {
  description = "Minimum number of GPU worker tasks (0 enables scale-to-zero)."
  type        = number
  default     = 0

  validation {
    condition     = var.worker_min_capacity >= 0 && floor(var.worker_min_capacity) == var.worker_min_capacity
    error_message = "worker_min_capacity must be a non-negative integer."
  }
}

variable "worker_max_capacity" {
  description = "Maximum number of GPU worker tasks (and GPU instances)."
  type        = number
  default     = 2

  validation {
    condition     = var.worker_max_capacity >= 1 && floor(var.worker_max_capacity) == var.worker_max_capacity
    error_message = "worker_max_capacity must be a positive integer."
  }
}

variable "api_desired_count" {
  description = "Baseline number of API tasks; CPU autoscaling can go up to twice this value (minimum 4)."
  type        = number
  default     = 1

  validation {
    condition     = var.api_desired_count >= 1 && floor(var.api_desired_count) == var.api_desired_count
    error_message = "api_desired_count must be a positive integer."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly AWS Budget limit in USD; alerts fire at 80 % actual and 100 % forecasted spend."
  type        = number
  default     = 150

  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "monthly_budget_usd must be greater than zero."
  }
}

variable "image_tag" {
  description = "Tag of the API and worker images in ECR to deploy (the CI passes the git SHA)."
  type        = string
  default     = "latest"
}

variable "supabase_url" {
  description = "Supabase project URL (https://<ref>.supabase.co) used by the API and the worker for PostgREST calls."
  type        = string

  validation {
    condition     = can(regex("^https://", var.supabase_url))
    error_message = "supabase_url must be an https:// URL."
  }
}

variable "job_timeout_seconds" {
  description = "JOB_TIMEOUT_SECONDS for the API/worker: jobs left running longer than this are reaped and their credit reservation released."
  type        = number
  default     = 180
}

variable "github_repository" {
  description = "GitHub repository (owner/name) allowed to assume the deploy role through OIDC."
  type        = string
  default     = "GregoryDich/GregoryDich"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be in the form owner/name."
  }
}

variable "create_github_oidc_provider" {
  description = "Create the token.actions.githubusercontent.com OIDC provider. Set to false when the account already has one."
  type        = bool
  default     = true
}

variable "enable_cloudfront" {
  description = "Serve job assets through a CloudFront distribution (OAC + signed URLs) instead of S3 presigned URLs."
  type        = bool
  default     = false
}

variable "cloudfront_public_key_pem" {
  description = "PEM-encoded RSA public key registered as a CloudFront trusted key for signed URLs. Required when enable_cloudfront is true."
  type        = string
  default     = ""
}

variable "alarm_email" {
  description = "E-mail address subscribed to the alarm/budget SNS topic. Optional for non-production environments; a prod/production environment refuses to plan without it (precondition in modules/observability), because alarms that reach nobody are silent failures."
  type        = string
  default     = ""
}

variable "sentry_dsn" {
  description = "SENTRY_DSN for the API and worker tasks; empty disables error reporting. The CI passes the SENTRY_DSN repository secret through TF_VAR_sentry_dsn."
  type        = string
  default     = ""
  sensitive   = true
}

variable "maintenance_mode" {
  description = "MAINTENANCE_MODE for the API tasks (kill switch): when true the API stops accepting new job submissions. The CI passes the MAINTENANCE_MODE repository variable through TF_VAR_maintenance_mode."
  type        = bool
  default     = false
}
