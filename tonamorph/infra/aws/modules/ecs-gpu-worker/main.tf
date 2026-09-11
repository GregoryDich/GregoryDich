locals {
  container_name = "worker"
}

data "aws_ssm_parameter" "ecs_gpu_ami" {
  name = var.ami_ssm_parameter
}

resource "aws_security_group" "worker" {
  name        = "${var.name}-worker"
  description = "GPU worker instances and tasks: outbound only"
  vpc_id      = var.vpc_id

  egress {
    description = "Outbound (ECR, S3, SQS, Secrets Manager, Supabase)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-worker" }
}

# ---------------------------------------------------------------------------
# EC2 capacity: launch template + ASG + ECS capacity provider
# ---------------------------------------------------------------------------

resource "aws_launch_template" "gpu" {
  name_prefix            = "${var.name}-gpu-"
  image_id               = data.aws_ssm_parameter.ecs_gpu_ami.value
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.worker.id]
  update_default_version = true

  iam_instance_profile {
    name = var.instance_profile_name
  }

  user_data = base64encode(<<-EOT
    #!/bin/bash
    cat <<'ECSCONFIG' >> /etc/ecs/ecs.config
    ECS_CLUSTER=${var.cluster_name}
    ECS_ENABLE_GPU_SUPPORT=true
    ECS_ENABLE_TASK_IAM_ROLE=true
    ECS_CONTAINER_STOP_TIMEOUT=2m
    ECS_IMAGE_PULL_BEHAVIOR=prefer-cached
    ECS_ENABLE_CONTAINER_METADATA=true
    ECSCONFIG
  EOT
  )

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.root_volume_gb
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  monitoring {
    enabled = true
  }

  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.name}-gpu-worker" }
  }

  tag_specifications {
    resource_type = "volume"
    tags          = { Name = "${var.name}-gpu-worker" }
  }
}

resource "aws_autoscaling_group" "gpu" {
  name                  = "${var.name}-gpu"
  min_size              = 0
  max_size              = var.max_capacity
  vpc_zone_identifier   = var.private_subnet_ids
  health_check_type     = "EC2"
  protect_from_scale_in = true # required for managed termination protection

  launch_template {
    id      = aws_launch_template.gpu.id
    version = "$Latest"
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }

  tag {
    key                 = "Name"
    value               = "${var.name}-gpu-worker"
    propagate_at_launch = true
  }

  # The capacity provider drives desired capacity from task demand.
  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_ecs_capacity_provider" "gpu" {
  name = "${var.name}-gpu"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.gpu.arn
    managed_termination_protection = "ENABLED"

    managed_scaling {
      status                    = "ENABLED"
      target_capacity           = 100
      minimum_scaling_step_size = 1
      maximum_scaling_step_size = 1
      instance_warmup_period    = 300
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = var.cluster_name
  capacity_providers = ["FARGATE", "FARGATE_SPOT", aws_ecs_capacity_provider.gpu.name]
}

# ---------------------------------------------------------------------------
# Worker task and service
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.name}/worker"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = local.container_name
      image     = var.image
      essential = true
      cpu       = var.cpu
      memory    = var.memory

      resourceRequirements = [
        { type = "GPU", value = "1" }
      ]

      environment = [for k, v in var.environment : { name = k, value = v }]
      secrets     = [for k, v in var.secrets : { name = k, valueFrom = v }]

      # Time for an in-flight job to finish and its message to be deleted.
      stopTimeout = 120

      linuxParameters = {
        sharedMemorySize = 2048
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "worker" {
  name                               = "${var.name}-worker"
  cluster                            = var.cluster_arn
  task_definition                    = aws_ecs_task_definition.worker.arn
  desired_count                      = var.min_capacity
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.gpu.name
    weight            = 1
    base              = 0
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_ecs_cluster_capacity_providers.this]
}

# ---------------------------------------------------------------------------
# Queue-driven scaling with scale-to-zero. Target tracking cannot reach zero
# tasks (the backlog-per-task metric is undefined at zero), so two step
# policies are used: scale out as soon as messages are visible, scale in to
# exactly zero once nothing is visible or in flight for 10 minutes.
# ---------------------------------------------------------------------------

resource "aws_appautoscaling_target" "worker" {
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.worker.name}"
  min_capacity       = var.min_capacity
  max_capacity       = var.max_capacity
}

resource "aws_appautoscaling_policy" "scale_out" {
  name               = "${var.name}-worker-scale-out"
  policy_type        = "StepScaling"
  service_namespace  = aws_appautoscaling_target.worker.service_namespace
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  resource_id        = aws_appautoscaling_target.worker.resource_id

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Maximum"

    # Bounds are relative to the alarm threshold (1 message).
    step_adjustment {
      metric_interval_lower_bound = 0
      metric_interval_upper_bound = 4
      scaling_adjustment          = 1
    }

    step_adjustment {
      metric_interval_lower_bound = 4
      scaling_adjustment          = 2
    }
  }
}

resource "aws_appautoscaling_policy" "scale_in" {
  name               = "${var.name}-worker-scale-in"
  policy_type        = "StepScaling"
  service_namespace  = aws_appautoscaling_target.worker.service_namespace
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  resource_id        = aws_appautoscaling_target.worker.resource_id

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 300
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_upper_bound = 0
      scaling_adjustment          = 0
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  alarm_name          = "${var.name}-worker-scale-out"
  alarm_description   = "Jobs are waiting in the queue: add GPU workers."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = var.job_queue_name
  }

  alarm_actions = [aws_appautoscaling_policy.scale_out.arn]
}

resource "aws_cloudwatch_metric_alarm" "queue_idle" {
  alarm_name          = "${var.name}-worker-scale-in"
  alarm_description   = "No job visible or in flight for 10 minutes: scale GPU workers to zero."
  evaluation_periods  = 10
  datapoints_to_alarm = 10
  threshold           = 0
  comparison_operator = "LessThanOrEqualToThreshold"
  treat_missing_data  = "breaching" # an idle queue stops emitting metrics

  metric_query {
    id          = "backlog"
    expression  = "visible + inflight"
    label       = "Queued + in-flight jobs"
    return_data = true
  }

  metric_query {
    id = "visible"

    metric {
      namespace   = "AWS/SQS"
      metric_name = "ApproximateNumberOfMessagesVisible"
      stat        = "Maximum"
      period      = 60

      dimensions = {
        QueueName = var.job_queue_name
      }
    }
  }

  metric_query {
    id = "inflight"

    metric {
      namespace   = "AWS/SQS"
      metric_name = "ApproximateNumberOfMessagesNotVisible"
      stat        = "Maximum"
      period      = 60

      dimensions = {
        QueueName = var.job_queue_name
      }
    }
  }

  alarm_actions = [aws_appautoscaling_policy.scale_in.arn]
}
