terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Partial configuration: pass bucket/key/region/dynamodb_table with
  # `terraform init -backend-config=backend.hcl` (see README.md, "Bootstrap").
  backend "s3" {}
}
