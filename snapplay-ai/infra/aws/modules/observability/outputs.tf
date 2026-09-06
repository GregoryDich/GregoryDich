output "sns_topic_arn" {
  description = "SNS topic that receives alarm state changes and budget notifications."
  value       = aws_sns_topic.alarms.arn
}
