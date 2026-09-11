# Tonamorph — AWS deployment (contract §10)

Terraform (>= 1.5, AWS provider ~> 5) for the default production path: FastAPI on
ECS Fargate behind an HTTPS ALB, a GPU worker on an EC2 capacity provider that
scales to zero, S3 for job assets, SQS with a dead-letter queue, Secrets Manager,
CloudWatch alarms and an AWS Budget.

```
plugin ──HTTPS──> ALB ──> ECS Fargate (api)  ──SQS──> ECS EC2 GPU (worker, g5.xlarge)
                            │  ▲                          │
                            │  └── reaper task (5 min)    ├── S3 jobs/<user>/<job>/ (24 h expiry)
                            └── Supabase (PostgREST)      └── Supabase (complete_job / fail_job)
```

## Layout

| path | what |
|------|------|
| `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` | root module: provider, ECR repositories, ECS cluster, module wiring |
| `modules/vpc` | 2-AZ VPC, public subnets (ALB, NAT), private subnets (tasks), S3 gateway endpoint |
| `modules/storage` | job bucket (SSE, public access blocked, 24 h lifecycle expiry), optional CloudFront with OAC and a trusted key group |
| `modules/queue` | job queue (visibility 300 s, long polling) + DLQ, redrive after 3 receives |
| `modules/iam` | execution/task roles (least privilege on `jobs/` prefix, SQS, secrets), ECS instance role, GitHub OIDC deploy role |
| `modules/secrets` | Secrets Manager placeholders (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `LEMONSQUEEZY_WEBHOOK_SECRET`, `PADDLE_WEBHOOK_SECRET`, plus `CLOUDFRONT_PRIVATE_KEY` when CloudFront is on) |
| `modules/ecs-api` | ACM certificate, ALB (HTTP→HTTPS, health check `/v1/health`), Fargate service with target-tracking CPU autoscaling, reaper scheduled task (`var.reaper_schedule_expression`, default `rate(5 minutes)`) |
| `modules/ecs-gpu-worker` | GPU launch template + ASG + capacity provider, worker task (GPU=1), step scaling on queue depth with scale-to-zero |
| `modules/observability` | SNS topic (production refuses to plan without `alarm_email`; optional SMS via `alarm_phone`), log metric filters on the API and worker log groups, alarms (DLQ depth, ALB 5xx rate, queue age, job failure rate, API error count), monthly budget with an 80 % alert and a kill-switch action at 100 % |
| `production.tfvars` | non-secret sizing for production |
| `backend.hcl.example` | template for the S3 backend configuration |

## Prerequisites

* Terraform >= 1.5 (the CI pins 1.9.8), AWS CLI v2, Docker with BuildKit.
* An AWS account and an IAM principal with administrator rights for the first apply
  (later applies run through the GitHub deploy role created here).
* A hosted zone for `domain_name` in Route 53 **or** an already-issued ACM
  certificate in the target region (see "TLS and DNS").

## Bootstrap: remote state

Terraform state lives in S3 with a DynamoDB lock table. Create both once per
account (names must match `backend.hcl` and the `TF_STATE_BUCKET` / `TF_LOCK_TABLE`
repository variables):

```bash
export AWS_REGION=us-east-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STATE_BUCKET="tonamorph-terraform-state-${ACCOUNT_ID}"

aws s3api create-bucket --bucket "$STATE_BUCKET" --region "$AWS_REGION" \
  $( [ "$AWS_REGION" != us-east-1 ] && echo --create-bucket-configuration LocationConstraint="$AWS_REGION" )
aws s3api put-bucket-versioning --bucket "$STATE_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$STATE_BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$STATE_BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws dynamodb create-table --table-name tonamorph-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

cp backend.hcl.example backend.hcl   # edit bucket/region, backend.hcl is git-ignored
```

## Apply order (first deployment)

Run from `tonamorph/infra/aws` with administrator credentials.

1. **Init** against the remote state:
   ```bash
   terraform init -backend-config=backend.hcl
   ```
2. **Create the registries first** so the images can be pushed before the ECS
   services reference them:
   ```bash
   export TF_VAR_supabase_url=https://<ref>.supabase.co
   export TF_VAR_route53_zone_id=Z0123456789   # or TF_VAR_acm_certificate_arn=arn:aws:acm:...
   terraform apply -var-file=production.tfvars -target=aws_ecr_repository.this
   ```
3. **Build and push both images** (context is `tonamorph/`):
   ```bash
   REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
   aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"
   cd ../..   # tonamorph/
   docker build -f infra/Dockerfile.api    -t "$REGISTRY/tonamorph-prod/api:latest"    .
   docker build -f infra/Dockerfile.worker -t "$REGISTRY/tonamorph-prod/worker:latest" .
   docker push "$REGISTRY/tonamorph-prod/api:latest"
   docker push "$REGISTRY/tonamorph-prod/worker:latest"
   cd infra/aws
   ```
4. **Full apply** (creates everything else; ~10 minutes, mostly ALB, NAT and the
   certificate validation):
   ```bash
   terraform apply -var-file=production.tfvars
   ```
5. **Populate the secrets** — the placeholders are `CHANGE_ME` and Terraform never
   overwrites them again (`ignore_changes`). All four are mandatory: with `ENV=production`
   the API refuses to start unless `SUPABASE_JWT_SECRET` (or a JWKS URL) **and both**
   webhook secrets are real, so a task that keeps crash-looping after the first deploy is
   usually a `CHANGE_ME` left in place:
   ```bash
   for s in SUPABASE_SERVICE_ROLE_KEY SUPABASE_JWT_SECRET LEMONSQUEEZY_WEBHOOK_SECRET PADDLE_WEBHOOK_SECRET; do
     aws secretsmanager put-secret-value --secret-id "tonamorph-prod/$s" --secret-string "$(read -rsp "$s: " v; echo "$v")"
   done
   aws ecs update-service --cluster tonamorph-prod --service tonamorph-prod-api --force-new-deployment
   ```
6. **Wire GitHub Actions** with `terraform output github_deploy_role_arn` (below).
7. Verify: `curl -i https://<domain_name>/v1/health` returns 200 and
   `terraform output` lists the queue URLs and bucket.
8. Verify the paywall can actually take money:
   `curl -s https://<domain_name>/v1/plans | jq -r '.plans[] | select(.price_usd > 0) | "\(.id) \(.checkout_url // "MISSING")"'`.
   A fresh database seeds `plans.provider_variant_ids` empty, so every `checkout_url` is
   `null` and the in-plugin paywall shows no buttons — silently. See `db/README.md`.

Later deployments are done by `.github/workflows/deploy.yml` (the workflows live at the
**repository root**, one level above `tonamorph/`): on every push to `main` it builds
and pushes both images tagged with the commit SHA, runs
`terraform plan -var image_tag=<sha>`, applies after approval of the `production`
GitHub environment, and then runs `python -m app.checks` as a one-off Fargate task on
the new API task definition (same network and secrets as the service; the task's log
lines are echoed into the job) — a paid plan without a checkout URL fails the workflow.
Note that no workflow runs `terraform validate` or `terraform fmt -check`; run them
yourself before pushing infrastructure changes.

## TLS and DNS

`domain_name` must resolve to the ALB over HTTPS. Two supported setups:

* **Route 53 (recommended):** set `route53_zone_id`. Terraform requests an ACM
  certificate, creates the DNS validation records, waits for issuance and creates
  an alias `A` record for `domain_name`.
* **DNS elsewhere:** request/validate a certificate manually in the same region,
  set `acm_certificate_arn`, and point a CNAME at `terraform output alb_dns_name`.

Setting neither fails the plan with an explicit precondition message.

## Variables

| variable | default | notes |
|----------|---------|-------|
| `region` | `us-east-1` | g5 availability varies by region |
| `project_name` / `environment` | `tonamorph` / `prod` | resource name prefix `tonamorph-prod` |
| `domain_name` | — | API hostname |
| `route53_zone_id` / `acm_certificate_arn` | `""` | one of them is required |
| `gpu_instance_type` | `g5.xlarge` | validated against `g5.*` / `g4dn.*` |
| `worker_min_capacity` / `worker_max_capacity` | `0` / `2` | worker tasks = GPU instances |
| `api_desired_count` | `1` | CPU autoscaling up to `max(2×, 4)` |
| `monthly_budget_usd` | `150` (`300` in `production.tfvars`) | account-wide budget: notification at 80 % actual and 100 % forecast, kill-switch action at 100 % actual |
| `image_tag` | `latest` | set by the CI to the git SHA |
| `supabase_url` | — | `SUPABASE_URL` for API and worker |
| `job_timeout_seconds` | `180` | `JOB_TIMEOUT_SECONDS`; the reaper releases jobs running longer |
| `github_repository` | `GregoryDich/GregoryDich` | OIDC trust: `main` branch and the `production` environment |
| `create_github_oidc_provider` | `true` | `false` if the account already has the GitHub provider |
| `enable_cloudfront` / `cloudfront_public_key_pem` | `false` / `""` | signed CloudFront URLs; also creates the `CLOUDFRONT_PRIVATE_KEY` secret |
| `alarm_email` | `""` | e-mail subscription on the alarm topic; **required when `environment` is `prod`/`production`** (a precondition fails the plan otherwise) |
| `alarm_phone` | `""` | E.164 number (`+14155550123`) subscribed to the alarm topic by SMS — the only channel that pages one person; see "Alarms" for the SNS sandbox step. Pass it as `TF_VAR_alarm_phone` or `-var alarm_phone=…` |
| `maintenance_mode` | `false` | `MAINTENANCE_MODE` on the API tasks: `true` stops new job submissions (kill switch) |
| `sentry_dsn` | `""` | `SENTRY_DSN` for API and worker; empty disables error reporting (sensitive; from the `SENTRY_DSN` repository secret) |
| `klaviyo_private_api_key` | `""` | `KLAVIYO_PRIVATE_API_KEY` for API and worker; empty disables growth events (sensitive; from the `KLAVIYO_PRIVATE_API_KEY` repository secret) |

## GitHub Actions configuration

Repository **variables** (Settings → Secrets and variables → Actions → Variables):

| variable | value |
|----------|-------|
| `AWS_REGION` | same as `region` |
| `AWS_DEPLOY_ROLE_ARN` | `terraform output -raw github_deploy_role_arn` |
| `TF_STATE_BUCKET` / `TF_LOCK_TABLE` | from the bootstrap step |
| `SUPABASE_URL` | Supabase project URL |
| `ROUTE53_ZONE_ID` or `ACM_CERTIFICATE_ARN` | see "TLS and DNS" (leave the other empty) |
| `ALARM_EMAIL` | **required** for the production environment (`terraform plan` fails when empty) |
| `ALARM_PHONE` | optional; `deploy.yml` passes it as `TF_VAR_alarm_phone` (E.164, see "Alarms" for the SNS sandbox step) |
| `MAINTENANCE_MODE` | optional; `true` redeploys the API with new job submissions disabled (kill switch), unset/`false` otherwise |

Repository **secrets** (optional, both may stay unset): `SENTRY_DSN` → `TF_VAR_sentry_dsn`, `KLAVIYO_PRIVATE_API_KEY` → `TF_VAR_klaviyo_private_api_key`; both reach the API and worker tasks as environment variables and an empty value disables the feature.

Create a GitHub **environment** named `production` with required reviewers; the
`apply` job waits for that approval. No long-lived AWS keys are stored: the deploy
role trusts the repository through OIDC and is limited to the `main` branch and the
`production` environment. It carries `PowerUserAccess` plus IAM rights restricted to
`tonamorph-prod-*` roles/policies, which is what `terraform apply` needs.

The committed `.terraform.lock.hcl` only records the `linux_amd64` checksum (it was
generated offline). Before the first apply from a macOS workstation run
`terraform providers lock -platform=linux_amd64 -platform=darwin_arm64 -platform=darwin_amd64`
and commit the result.

## GPU cost: g5.xlarge vs g4dn.xlarge

On-demand list prices in us-east-1 (Linux, per hour, billed per second after the
first minute; verify current prices in the AWS pricing calculator):

| | g5.xlarge (A10G 24 GB) | g4dn.xlarge (T4 16 GB) |
|---|---|---|
| on-demand | ≈ $1.01/h | ≈ $0.53/h |
| spot (typical) | ≈ $0.40–0.50/h | ≈ $0.16–0.25/h |
| pipeline time for a 30 s clip (contract §7) | ≈ 2.0 s | ≈ 5 s |
| compute per job | ≈ $0.0006 | ≈ $0.0007 |
| jobs per busy hour (serial) | ≈ 1 800 | ≈ 700 |

The T4 is cheaper per hour but slower per job, so the per-job cost is about the
same while the user-facing latency is 2.5× worse. `g5.xlarge` is the default; use
`g4dn.xlarge` only if g5 capacity is unavailable in the region, and then advertise
a ~5 s target instead of 2 s.

With `worker_min_capacity = 0` no GPU instance runs while the queue is idle. A cold
start (instance boot, ~8 GB image pull, model load) takes 3–5 minutes; set
`worker_min_capacity = 1` (≈ $735/month on-demand for g5.xlarge) if that latency
is unacceptable for the first job of the day.

Always-on baseline independent of the GPU (us-east-1, approximate): NAT gateway
≈ $33 + data, ALB ≈ $17 + LCUs, one Fargate task 0.5 vCPU/1 GB ≈ $18, Secrets
Manager ≈ $2, CloudWatch/ECR/EBS a few dollars — about $75/month. The production
budget of $300 (`production.tfvars`) leaves ≈ $225 for GPU hours (≈ 220 busy A10G
hours); the variable default of $150 is meant for smaller environments.

## Reaper scheduled task

`modules/ecs-api` defines an EventBridge rule (`rate(5 minutes)`) whose target is a
one-off Fargate task on the cluster, running the **API image** with the container
command overridden to `python -m app.services.aws.reaper`. The task uses the API's
task/execution roles and security group and logs to `/ecs/tonamorph-prod/api`. The
reaper marks jobs left `running` past `JOB_TIMEOUT_SECONDS` as failed and releases
their credit reservation, so a worker that dies mid-job never silently consumes a
credit (contract §10). `infra/supabase/cleanup.sql` schedules the same guarantee
inside the database for non-AWS deployments.

## Worker scaling

* Scale out: the `tonamorph-prod-worker-scale-out` alarm fires when
  `ApproximateNumberOfMessagesVisible >= 1` and adds 1 task (2 when 5+ messages).
* Scale in: `tonamorph-prod-worker-scale-in` fires after 10 minutes with
  `visible + in-flight == 0` (missing data counts as idle) and sets the desired
  count to exactly `worker_min_capacity`.
* The capacity provider (managed scaling, target 100 %, managed termination
  protection) launches and terminates GPU instances to match the task count and
  never terminates an instance that still runs a task.

## Alarms

Every alarm and budget notification is published to the `tonamorph-prod-alarms` SNS
topic. `alarm_email` subscribes an address (mandatory in production; e-mail is a
digest, not a page). `alarm_phone` adds an SMS subscription — the only channel that
wakes one person up — and is opt-in:

1. Set `alarm_phone` to the number in E.164 form (`+14155550123`), apply.
2. New accounts sit in the **SNS SMS sandbox**: open SNS → Text messaging (SMS) →
   Sandbox destination phone numbers, add the same number and enter the verification
   code, or request production access. Until then SNS silently drops the messages.
3. Check the account-level SMS spend limit (default 1 USD/month) under Text messaging
   preferences; a noisy week can exhaust it.

| alarm | fires when | what it means / what to do |
|---|---|---|
| `…-dlq-depth` | any message in the dead-letter queue (3 failed receives) | A job crashed the worker three times. Read the worker log, fix, then redrive (see Operations). The reaper already released the credit. |
| `…-worker-queue-age` | the oldest queued job waited > 10 min for 5 min | Workers are not starting (GPU capacity, image pull, crash loop) or cannot keep up. Check the ASG and the worker log. |
| `…-alb-5xx-rate` | > 5 % of ALB requests answered 5xx in 3 of 5 minutes | The API is failing or unreachable; plugins see errors on every call. Check the API log and target health. |
| `…-job-failure-rate` | failed jobs ≥ 10 % of jobs submitted in a 15-minute window with ≥ 20 submissions | The SLO (≥ 99 % of reserved jobs captured) is being missed. Failures are counted from the logs: worker `job rejected` and `job attempt N failed` lines (every attempt counts, so a crash loop trips it fast), API `job hand-off failed`, and the reaper's `reaped N stale job(s)`. Below 90 % over 15 min, flip `MAINTENANCE_MODE=true` (users are not charged either way). |
| `…-api-error-count` | ≥ 10 API log lines with `"level": "ERROR"` in 5 minutes | Unhandled exceptions or upstream failures (Supabase, SQS, S3). Open the API log group and Sentry. |
| budget 80 % | actual spend passed 80 % of `monthly_budget_usd` | Heads-up; nothing changes. |
| budget 100 % forecast | forecast spend will pass 100 % | Heads-up; nothing changes. |
| budget 100 % actual (action) | actual spend passed 100 % | The kill switch attaches the deny-intake policy (see Operations). |

The metric filters publish to the custom namespace `tonamorph-prod/jobs` (`ApiErrors`,
`JobsSubmitted`, `JobsFailed`); they match the exact log shapes documented in
`modules/observability/main.tf`, so a change to those log lines must update the
patterns in the same commit. Missing data never breaches: a quiet night stays green.

## Operations

* Logs: `aws logs tail /ecs/tonamorph-prod/api --follow`, same for `worker`.
* Redrive the DLQ after a fix: `aws sqs start-message-move-task --source-arn <dlq-arn>`.
* Alarms and budget notifications go to the `tonamorph-prod-alarms` SNS topic; set
  `alarm_email` (mandatory in production) and `alarm_phone` for SMS (see "Alarms").
* **Budget kill switch.** At 100 % of `monthly_budget_usd` (actual spend) the budget
  action attaches `tonamorph-prod-budget-deny-job-intake` (Deny `sqs:SendMessage` on the
  job queue) to the API task role: `POST /v1/jobs` answers `503 worker_unavailable` and
  releases the credit, nothing new is enqueued, in-flight jobs finish and the scale-in
  alarm returns the worker service to `worker_min_capacity` after ten minutes. Budgets
  actions cannot change ECS/ASG counts, so a non-zero `worker_min_capacity` still has to
  be scaled down by hand. The policy stays attached until you reset the action:
  `aws budgets execute-budget-action --account-id <id> --budget-name tonamorph-prod-monthly --action-id $(terraform output -raw budget_action_id) --execution-type RESET_BUDGET_ACTION`.
* **Maintenance mode.** Set the `MAINTENANCE_MODE` repository variable to `true` and
  re-run `deploy.yml` (or `terraform apply -var maintenance_mode=true`) to stop accepting
  jobs without touching the budget.
* Force a redeploy of the current image tag:
  `aws ecs update-service --cluster tonamorph-prod --service tonamorph-prod-api --force-new-deployment`.
* Tear down: `terraform destroy -var-file=production.tfvars` (empty the job bucket
  first if it still holds objects; secrets stay recoverable for 7 days).
