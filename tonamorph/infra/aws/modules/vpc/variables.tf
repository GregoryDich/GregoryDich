variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "cidr_block" {
  description = "VPC CIDR block; subnets are carved as /20s from it."
  type        = string
  default     = "10.42.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones (one public and one private subnet each)."
  type        = number
  default     = 2
}
