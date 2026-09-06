variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "visibility_timeout_seconds" {
  description = "Initial visibility timeout; the worker extends it while a job is processing."
  type        = number
  default     = 300
}

variable "message_retention_seconds" {
  description = "How long an unprocessed job message is kept before SQS drops it."
  type        = number
  default     = 86400
}

variable "max_receive_count" {
  description = "Receives before a message is moved to the dead-letter queue."
  type        = number
  default     = 3
}
