# Non-secret sizing for the production environment. Values that differ per
# account (supabase_url, route53_zone_id / acm_certificate_arn) are supplied by
# the CI through TF_VAR_* environment variables, see ../../infra/aws/README.md.
region              = "us-east-1"
project_name        = "tonamorph"
environment         = "prod"
domain_name         = "api.tonamorph.com"
gpu_instance_type   = "g5.xlarge"
worker_min_capacity = 0
worker_max_capacity = 2
api_desired_count   = 1
monthly_budget_usd  = 150
