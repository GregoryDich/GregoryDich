data "aws_iam_policy_document" "sns_topic" {
  statement {
    sid       = "AllowAlarmsAndBudgets"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alarms.arn]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com", "budgets.amazonaws.com"]
    }
  }
}

resource "aws_sns_topic" "alarms" {
  name = "${var.name}-alarms"

  lifecycle {
    # Terraform variable validation cannot look at another variable, so the
    # "production needs a subscriber" rule lives here and fails the plan.
    precondition {
      condition     = !var.require_alarm_email || var.alarm_email != ""
      error_message = "alarm_email is empty for a production environment: every alarm and budget notification would go to a topic with no subscriber. Set the ALARM_EMAIL repository variable (TF_VAR_alarm_email) or pass -var alarm_email=..."
    }
  }
}

resource "aws_sns_topic_policy" "alarms" {
  arn    = aws_sns_topic.alarms.arn
  policy = data.aws_iam_policy_document.sns_topic.json
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alarm_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# SMS is the only channel that wakes one person up. New AWS accounts start in the
# SNS SMS sandbox: the number has to be verified in the SNS console (Text messaging →
# Sandbox destination phone numbers) before a single message is delivered, and the
# account-level monthly SMS spend limit (default 1 USD) may need raising.
resource "aws_sns_topic_subscription" "sms" {
  count = var.alarm_phone != "" ? 1 : 0

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "sms"
  endpoint  = var.alarm_phone
}

# ---------------------------------------------------------------------------
# Log metric filters
#
# The API (app.main.JsonFormatter) writes one JSON object per line:
#   {"ts": ..., "level": "ERROR", "logger": ..., "msg": ..., <extra fields>}
# and one "request" access line per HTTP request with method, path and status.
# The GPU worker (worker.aws_worker) and the reaper (app.services.aws.reaper, run
# as a one-off task in the API image, hence the API log group) use plain text:
#   2026-09-11 14:05:00,123 LEVEL logger.name message
# The patterns below match those exact shapes; change them together with the
# log lines they name.
# ---------------------------------------------------------------------------

locals {
  metrics_namespace = "${var.name}/jobs"
}

resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${var.name}-api-errors"
  log_group_name = var.api_log_group_name
  pattern        = "{ $.level = \"ERROR\" }"

  metric_transformation {
    name          = "ApiErrors"
    namespace     = local.metrics_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# Denominator of the failure rate: every accepted POST /v1/jobs (202 per contract §2).
resource "aws_cloudwatch_log_metric_filter" "jobs_submitted" {
  name           = "${var.name}-jobs-submitted"
  log_group_name = var.api_log_group_name
  pattern        = "{ ($.msg = \"request\") && ($.method = \"POST\") && ($.path = \"/v1/jobs\") && ($.status = 202) }"

  metric_transformation {
    name          = "JobsSubmitted"
    namespace     = local.metrics_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# app/routers/jobs.py: the queue refused the job after it was created (credit released).
resource "aws_cloudwatch_log_metric_filter" "jobs_handoff_failed" {
  name           = "${var.name}-jobs-handoff-failed"
  log_group_name = var.api_log_group_name
  pattern        = "{ $.msg = \"job hand-off failed\" }"

  metric_transformation {
    name          = "JobsFailed"
    namespace     = local.metrics_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# app/services/aws/reaper.py: "reaped N stale job(s) running longer than Ts" — N jobs
# failed because a worker died mid-job. The count is read from the sixth field.
resource "aws_cloudwatch_log_metric_filter" "jobs_reaped" {
  name           = "${var.name}-jobs-reaped"
  log_group_name = var.api_log_group_name
  pattern        = "[date, time, level, logger = \"tonamorph.aws.reaper\", word = \"reaped\", count, ...]"

  metric_transformation {
    name          = "JobsFailed"
    namespace     = local.metrics_namespace
    value         = "$count"
    default_value = "0"
    unit          = "Count"
  }
}

# worker/aws_worker.py: "job rejected: <message> (<code>)" (input the pipeline refused,
# job failed, message deleted) and "job attempt N failed" (pipeline crashed; the job is
# failed on the last attempt, earlier attempts are redelivered). Every failed attempt
# counts, so a crash loop reaches the threshold sooner rather than later.
resource "aws_cloudwatch_log_metric_filter" "jobs_failed_worker" {
  name           = "${var.name}-jobs-failed-worker"
  log_group_name = var.worker_log_group_name
  pattern        = "?\"job rejected\" ?\"job attempt\""

  metric_transformation {
    name          = "JobsFailed"
    namespace     = local.metrics_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# ---------------------------------------------------------------------------
# Alarms
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "job_failure_rate" {
  alarm_name          = "${var.name}-job-failure-rate"
  alarm_description   = "At least ${var.job_failure_rate_threshold_percent}% of jobs submitted in the last 15 minutes failed (rejected input, pipeline crash, hand-off failure or reaped), with at least ${var.job_failure_rate_min_jobs} submissions in the window. SLO: >= 99% of reserved jobs captured."
  evaluation_periods  = 1
  threshold           = var.job_failure_rate_threshold_percent
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "rate"
    expression  = "IF(submitted >= ${var.job_failure_rate_min_jobs}, FILL(failed, 0) / submitted * 100, 0)"
    label       = "Job failure rate (%)"
    return_data = true
  }

  metric_query {
    id = "submitted"

    metric {
      namespace   = local.metrics_namespace
      metric_name = "JobsSubmitted"
      stat        = "Sum"
      period      = 900
    }
  }

  metric_query {
    id = "failed"

    metric {
      namespace   = local.metrics_namespace
      metric_name = "JobsFailed"
      stat        = "Sum"
      period      = 900
    }
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  depends_on = [
    aws_cloudwatch_log_metric_filter.jobs_submitted,
    aws_cloudwatch_log_metric_filter.jobs_handoff_failed,
    aws_cloudwatch_log_metric_filter.jobs_reaped,
    aws_cloudwatch_log_metric_filter.jobs_failed_worker,
  ]
}

resource "aws_cloudwatch_metric_alarm" "api_error_count" {
  alarm_name          = "${var.name}-api-error-count"
  alarm_description   = "The API logged at least ${var.api_error_count_threshold} ERROR lines in 5 minutes (unhandled exceptions, failed hand-offs, upstream failures)."
  namespace           = local.metrics_namespace
  metric_name         = "ApiErrors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.api_error_count_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  depends_on = [aws_cloudwatch_log_metric_filter.api_errors]
}

resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  alarm_name          = "${var.name}-dlq-depth"
  alarm_description   = "Job messages landed in the dead-letter queue after 3 failed receives."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = var.dlq_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "worker_queue_age" {
  alarm_name          = "${var.name}-worker-queue-age"
  alarm_description   = "Oldest job message has waited longer than ${var.queue_age_threshold_seconds}s: workers are not keeping up or not starting."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 5
  datapoints_to_alarm = 5
  threshold           = var.queue_age_threshold_seconds
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = var.job_queue_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx_rate" {
  alarm_name          = "${var.name}-alb-5xx-rate"
  alarm_description   = "More than ${var.alb_5xx_rate_threshold_percent}% of ALB requests returned 5xx (ALB or target) over 3 of the last 5 minutes."
  evaluation_periods  = 5
  datapoints_to_alarm = 3
  threshold           = var.alb_5xx_rate_threshold_percent
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "rate"
    expression  = "IF(requests > 0, (elb_5xx + target_5xx) / requests * 100, 0)"
    label       = "5xx rate (%)"
    return_data = true
  }

  metric_query {
    id = "requests"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      stat        = "Sum"
      period      = 60

      dimensions = {
        LoadBalancer = var.alb_arn_suffix
      }
    }
  }

  metric_query {
    id = "elb_5xx"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_ELB_5XX_Count"
      stat        = "Sum"
      period      = 60

      dimensions = {
        LoadBalancer = var.alb_arn_suffix
      }
    }
  }

  metric_query {
    id = "target_5xx"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      stat        = "Sum"
      period      = 60

      dimensions = {
        LoadBalancer = var.alb_arn_suffix
      }
    }
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

resource "aws_budgets_budget" "monthly" {
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.alarms.arn]
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [aws_sns_topic.alarms.arn]
  }

  depends_on = [aws_sns_topic_policy.alarms]
}

# ---------------------------------------------------------------------------
# Kill switch at 100 % of the budget.
#
# AWS Budgets actions can only apply an IAM policy, an SCP or run the two SSM
# stop-instance documents; none of them can set an ECS service or ASG desired
# count. The closest native equivalent: attach a Deny on sqs:SendMessage for the
# job queue to the API task role. POST /v1/jobs then answers 503
# worker_unavailable and releases the credit in the same request (contract §2),
# nothing new reaches the queue, the workers finish what is in flight and the
# scale-in alarm (ecs-gpu-worker) brings the service back to worker_min_capacity
# ten minutes later. With worker_min_capacity = 0 that is zero GPU spend. The
# policy stays attached until an operator resets the action:
#   aws budgets execute-budget-action --account-id <id> --budget-name <name> #     --action-id <budget_action_id output> --execution-type RESET_BUDGET_ACTION
# (or detaches the policy by hand). Raise worker_min_capacity back only after that.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "deny_job_intake" {
  statement {
    sid       = "BudgetExceededDenyJobIntake"
    effect    = "Deny"
    actions   = ["sqs:SendMessage"]
    resources = [var.job_queue_arn]
  }
}

resource "aws_iam_policy" "deny_job_intake" {
  name        = "${var.name}-budget-deny-job-intake"
  description = "Attached to the API task role by the budget action: no new jobs are enqueued once the monthly budget is spent."
  policy      = data.aws_iam_policy_document.deny_job_intake.json
}

data "aws_iam_policy_document" "budget_action_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }
  }
}

resource "aws_iam_role" "budget_action" {
  name               = "${var.name}-budget-action"
  assume_role_policy = data.aws_iam_policy_document.budget_action_assume.json
}

data "aws_iam_policy_document" "budget_action" {
  statement {
    sid       = "AttachDetachKillSwitchPolicy"
    effect    = "Allow"
    actions   = ["iam:AttachRolePolicy", "iam:DetachRolePolicy"]
    resources = [var.api_task_role_arn]

    condition {
      test     = "ArnEquals"
      variable = "iam:PolicyARN"
      values   = [aws_iam_policy.deny_job_intake.arn]
    }
  }
}

resource "aws_iam_role_policy" "budget_action" {
  name   = "apply-kill-switch"
  role   = aws_iam_role.budget_action.id
  policy = data.aws_iam_policy_document.budget_action.json
}

resource "aws_budgets_budget_action" "stop_job_intake" {
  budget_name        = aws_budgets_budget.monthly.name
  action_type        = "APPLY_IAM_POLICY"
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.budget_action.arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 100
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.deny_job_intake.arn
      roles      = [var.api_task_role_name]
    }
  }

  subscriber {
    address           = aws_sns_topic.alarms.arn
    subscription_type = "SNS"
  }

  depends_on = [aws_iam_role_policy.budget_action, aws_sns_topic_policy.alarms]
}
