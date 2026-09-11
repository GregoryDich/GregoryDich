output "sns_topic_arn" {
  description = "SNS topic that receives alarm state changes and budget notifications."
  value       = aws_sns_topic.alarms.arn
}

output "budget_action_id" {
  description = "Id of the budget action that denies job intake at 100 % of the budget."
  value       = aws_budgets_budget_action.stop_job_intake.action_id
}
