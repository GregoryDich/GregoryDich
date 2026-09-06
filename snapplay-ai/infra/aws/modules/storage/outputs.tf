output "bucket_name" {
  description = "Job asset bucket name (S3_BUCKET)."
  value       = aws_s3_bucket.jobs.bucket
}

output "bucket_arn" {
  description = "Job asset bucket ARN."
  value       = aws_s3_bucket.jobs.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain (CLOUDFRONT_DOMAIN), empty when disabled."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.jobs[0].domain_name : ""
}

output "cloudfront_key_pair_id" {
  description = "Id of the trusted public key (CLOUDFRONT_KEY_PAIR_ID), empty when disabled."
  value       = var.enable_cloudfront ? aws_cloudfront_public_key.signing[0].id : ""
}

output "cloudfront_distribution_arn" {
  description = "Distribution ARN, empty when disabled."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.jobs[0].arn : ""
}
