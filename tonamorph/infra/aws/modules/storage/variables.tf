variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "account_id" {
  description = "AWS account id, appended to the bucket name for global uniqueness."
  type        = string
}

variable "enable_cloudfront" {
  description = "Create a CloudFront distribution in front of the bucket (OAC + trusted key group)."
  type        = bool
  default     = false
}

variable "cloudfront_public_key_pem" {
  description = "PEM-encoded RSA-2048 public key registered as the trusted signing key."
  type        = string
  default     = ""
}
