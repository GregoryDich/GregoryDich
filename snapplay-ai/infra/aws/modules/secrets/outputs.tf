output "secret_arns" {
  description = "Map of environment variable name to Secrets Manager secret ARN."
  value       = { for k, s in aws_secretsmanager_secret.this : k => s.arn }
}
