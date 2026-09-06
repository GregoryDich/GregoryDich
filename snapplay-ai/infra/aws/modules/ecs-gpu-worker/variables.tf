variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "region" {
  description = "AWS region (awslogs driver)."
  type        = string
}

variable "cluster_name" {
  description = "ECS cluster name."
  type        = string
}

variable "cluster_arn" {
  description = "ECS cluster ARN."
  type        = string
}

variable "vpc_id" {
  description = "VPC id."
  type        = string
}

variable "private_subnet_ids" {
  description = "Subnets for GPU instances and worker tasks."
  type        = list(string)
}

variable "image" {
  description = "Full worker image URI including tag."
  type        = string
}

variable "instance_type" {
  description = "GPU instance type (g5.* or g4dn.*)."
  type        = string
}

variable "ami_ssm_parameter" {
  description = "SSM parameter resolving to the ECS GPU-optimised AMI. Use /aws/service/ecs/optimized-ami/amazon-linux-2/gpu/recommended/image_id for the Amazon Linux 2 variant."
  type        = string
  default     = "/aws/service/ecs/optimized-ami/amazon-linux-2023/gpu/recommended/image_id"
}

variable "root_volume_gb" {
  description = "Root EBS volume size; the CUDA worker image and model weights need tens of GB."
  type        = number
  default     = 100
}

variable "min_capacity" {
  description = "Minimum worker tasks (0 = scale to zero)."
  type        = number
}

variable "max_capacity" {
  description = "Maximum worker tasks; also the ASG max size (one task per GPU instance)."
  type        = number
}

variable "job_queue_name" {
  description = "SQS job queue name driving the scaling alarms."
  type        = string
}

variable "execution_role_arn" {
  description = "Task execution role ARN."
  type        = string
}

variable "task_role_arn" {
  description = "Task role ARN."
  type        = string
}

variable "instance_profile_name" {
  description = "Instance profile for the ECS container instances."
  type        = string
}

variable "cpu" {
  description = "CPU units reserved by the worker container (g5/g4dn.xlarge have 4096)."
  type        = number
  default     = 3072
}

variable "memory" {
  description = "Hard memory limit of the worker container in MiB (xlarge instances have 16 GiB; leave headroom for the agent)."
  type        = number
  default     = 12288
}

variable "environment" {
  description = "Plain environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Environment variables injected from Secrets Manager (name => secret ARN)."
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 14
}
