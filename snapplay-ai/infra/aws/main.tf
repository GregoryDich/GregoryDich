provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

data "aws_caller_identity" "current" {}

locals {
  name          = "${var.project_name}-${var.environment}"
  is_production = contains(["prod", "production"], var.environment)

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  ecr_registry = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
  api_image    = "${local.ecr_registry}/${aws_ecr_repository.this["api"].name}:${var.image_tag}"
  worker_image = "${local.ecr_registry}/${aws_ecr_repository.this["worker"].name}:${var.image_tag}"

  # Non-secret configuration shared by the API and the worker (contract §10).
  common_environment = merge(
    {
      AWS_REGION          = var.region
      S3_BUCKET           = module.storage.bucket_name
      SQS_JOB_QUEUE_URL   = module.queue.job_queue_url
      SQS_DLQ_URL         = module.queue.dlq_url
      JOB_TIMEOUT_SECONDS = tostring(var.job_timeout_seconds)
      GPU_INSTANCE_TYPE   = var.gpu_instance_type
      SUPABASE_URL        = var.supabase_url
    },
    var.enable_cloudfront ? {
      CLOUDFRONT_DOMAIN      = module.storage.cloudfront_domain_name
      CLOUDFRONT_KEY_PAIR_ID = module.storage.cloudfront_key_pair_id
    } : {}
  )

  cloudfront_secrets = var.enable_cloudfront ? {
    CLOUDFRONT_PRIVATE_KEY = module.secrets.secret_arns["CLOUDFRONT_PRIVATE_KEY"]
  } : {}

  api_secrets = merge({
    SUPABASE_SERVICE_ROLE_KEY   = module.secrets.secret_arns["SUPABASE_SERVICE_ROLE_KEY"]
    SUPABASE_JWT_SECRET         = module.secrets.secret_arns["SUPABASE_JWT_SECRET"]
    LEMONSQUEEZY_WEBHOOK_SECRET = module.secrets.secret_arns["LEMONSQUEEZY_WEBHOOK_SECRET"]
    PADDLE_WEBHOOK_SECRET       = module.secrets.secret_arns["PADDLE_WEBHOOK_SECRET"]
  }, local.cloudfront_secrets)

  worker_secrets = merge({
    SUPABASE_SERVICE_ROLE_KEY = module.secrets.secret_arns["SUPABASE_SERVICE_ROLE_KEY"]
  }, local.cloudfront_secrets)
}

# ---------------------------------------------------------------------------
# Container registry and cluster (shared by both services)
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "this" {
  for_each = toset(["api", "worker"])

  name                 = "${local.name}/${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this

  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the 20 most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecs_cluster" "this" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

module "vpc" {
  source = "./modules/vpc"

  name = local.name
}

module "storage" {
  source = "./modules/storage"

  name                      = local.name
  account_id                = data.aws_caller_identity.current.account_id
  enable_cloudfront         = var.enable_cloudfront
  cloudfront_public_key_pem = var.cloudfront_public_key_pem
}

module "queue" {
  source = "./modules/queue"

  name = local.name
}

module "secrets" {
  source = "./modules/secrets"

  name                           = local.name
  include_cloudfront_private_key = var.enable_cloudfront
}

module "iam" {
  source = "./modules/iam"

  name                        = local.name
  account_id                  = data.aws_caller_identity.current.account_id
  bucket_arn                  = module.storage.bucket_arn
  job_queue_arn               = module.queue.job_queue_arn
  dlq_arn                     = module.queue.dlq_arn
  api_secret_arns             = values(local.api_secrets)
  worker_secret_arns          = values(local.worker_secrets)
  github_repository           = var.github_repository
  create_github_oidc_provider = var.create_github_oidc_provider
}

module "ecs_api" {
  source = "./modules/ecs-api"

  name                = local.name
  region              = var.region
  cluster_name        = aws_ecs_cluster.this.name
  cluster_arn         = aws_ecs_cluster.this.arn
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  private_subnet_ids  = module.vpc.private_subnet_ids
  image               = local.api_image
  domain_name         = var.domain_name
  route53_zone_id     = var.route53_zone_id
  acm_certificate_arn = var.acm_certificate_arn
  execution_role_arn  = module.iam.api_execution_role_arn
  task_role_arn       = module.iam.api_task_role_arn
  desired_count       = var.api_desired_count
  max_count           = max(var.api_desired_count * 2, 4)
  environment = merge(local.common_environment, {
    SNAPPLAY_PIPELINE = "aws"
    SERVICE_ROLE      = "api"
    MAINTENANCE_MODE  = tostring(var.maintenance_mode)
    SENTRY_DSN        = var.sentry_dsn
  })
  secrets = local.api_secrets
}

module "ecs_gpu_worker" {
  source = "./modules/ecs-gpu-worker"

  name                  = local.name
  region                = var.region
  cluster_name          = aws_ecs_cluster.this.name
  cluster_arn           = aws_ecs_cluster.this.arn
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  image                 = local.worker_image
  instance_type         = var.gpu_instance_type
  min_capacity          = var.worker_min_capacity
  max_capacity          = var.worker_max_capacity
  job_queue_name        = module.queue.job_queue_name
  execution_role_arn    = module.iam.worker_execution_role_arn
  task_role_arn         = module.iam.worker_task_role_arn
  instance_profile_name = module.iam.ecs_instance_profile_name
  environment = merge(local.common_environment, {
    WORKER_MODE       = "aws"
    SERVICE_ROLE      = "worker"
    SNAPPLAY_PIPELINE = "local"
    SENTRY_DSN        = var.sentry_dsn
  })
  secrets = local.worker_secrets
}

module "observability" {
  source = "./modules/observability"

  name                = local.name
  job_queue_name      = module.queue.job_queue_name
  dlq_name            = module.queue.dlq_name
  alb_arn_suffix      = module.ecs_api.alb_arn_suffix
  monthly_budget_usd  = var.monthly_budget_usd
  alarm_email         = var.alarm_email
  require_alarm_email = local.is_production
  account_id          = data.aws_caller_identity.current.account_id
  job_queue_arn       = module.queue.job_queue_arn
  api_task_role_name  = module.iam.api_task_role_name
  api_task_role_arn   = module.iam.api_task_role_arn
}
