variable "name" {
  description = "Resource name prefix; secrets are created as <name>/<KEY>."
  type        = string
}

variable "include_cloudfront_private_key" {
  description = "Also create the CLOUDFRONT_PRIVATE_KEY secret used to sign CloudFront URLs."
  type        = bool
  default     = false
}

variable "recovery_window_in_days" {
  description = "Days a deleted secret stays recoverable (7 keeps destroy/apply cycles short)."
  type        = number
  default     = 7
}
