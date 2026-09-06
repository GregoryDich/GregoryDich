output "job_queue_url" {
  description = "Job queue URL."
  value       = aws_sqs_queue.jobs.url
}

output "job_queue_arn" {
  description = "Job queue ARN."
  value       = aws_sqs_queue.jobs.arn
}

output "job_queue_name" {
  description = "Job queue name (CloudWatch QueueName dimension)."
  value       = aws_sqs_queue.jobs.name
}

output "dlq_url" {
  description = "Dead-letter queue URL."
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "Dead-letter queue ARN."
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_name" {
  description = "Dead-letter queue name (CloudWatch QueueName dimension)."
  value       = aws_sqs_queue.dlq.name
}
