# Modal deployment (alternative GPU path)

`TONAMORPH_PIPELINE=modal` runs the audio pipeline (contract §7) on Modal instead of
the AWS GPU worker. The API calls the deployed function; nothing changes for the
plugin. Use it for staging or when the AWS path is not provisioned.

## Prerequisites

```bash
pip install modal
modal token new          # interactive; CI uses MODAL_TOKEN_ID / MODAL_TOKEN_SECRET instead
```

## Secrets

The Modal function completes jobs through PostgREST with the service-role key and
uploads results to storage. Create the secrets once per Modal workspace:

```bash
# Supabase access for complete_job / fail_job and Storage uploads
modal secret create tonamorph-supabase \
  SUPABASE_URL=https://<ref>.supabase.co \
  SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# Optional: S3 / Cloudflare R2 instead of Supabase Storage (contract §10)
modal secret create tonamorph-s3 \
  AWS_REGION=us-east-1 \
  AWS_ACCESS_KEY_ID=<key> \
  AWS_SECRET_ACCESS_KEY=<secret> \
  S3_BUCKET=<bucket> \
  S3_ENDPOINT_URL=            # leave empty for AWS, set for R2
```

Rotate a secret with `modal secret create --force <name> KEY=value`. Never put these
values in `.env` files that are committed.

## Deploy

From the `tonamorph/` directory:

```bash
modal deploy backend/worker/modal_app.py
```

The first deploy builds the image (CUDA, Demucs v4, Basic Pitch) and takes several
minutes; later deploys reuse the cached layers. `modal app list` shows the deployed
app and `modal app logs <app-name>` streams its logs.

## Point the API at Modal

Set on the API service (ECS task definition, docker-compose or `.env`):

```
TONAMORPH_PIPELINE=modal
MODAL_TOKEN_ID=<token id>
MODAL_TOKEN_SECRET=<token secret>
```

The API looks up the deployed function by the app and function names declared in
`backend/worker/modal_app.py`.

## GPU choice and latency

The 2.0 s budget in contract §7 assumes an A10G. Keep the function on `gpu="A10G"`;
on a T4 separation alone takes 3-5 s, so a T4 deployment must advertise a ~5 s target.
Model weights are downloaded on first use; mount a `modal.Volume` on the cache
directory (`TORCH_HOME`) so cold starts do not re-download them.
