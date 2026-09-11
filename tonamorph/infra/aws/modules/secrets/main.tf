locals {
  secret_names = concat(
    [
      "SUPABASE_SERVICE_ROLE_KEY",
      "SUPABASE_JWT_SECRET",
      "LEMONSQUEEZY_WEBHOOK_SECRET",
      "PADDLE_WEBHOOK_SECRET",
    ],
    var.include_cloudfront_private_key ? ["CLOUDFRONT_PRIVATE_KEY"] : []
  )
}

resource "aws_secretsmanager_secret" "this" {
  for_each = toset(local.secret_names)

  name                    = "${var.name}/${each.key}"
  description             = "${each.key} for ${var.name}; set the real value with `aws secretsmanager put-secret-value`."
  recovery_window_in_days = var.recovery_window_in_days
}

# The placeholder is written once; real values are set out of band and
# ignore_changes keeps Terraform from ever reverting them.
resource "aws_secretsmanager_secret_version" "placeholder" {
  for_each = aws_secretsmanager_secret.this

  secret_id     = each.value.id
  secret_string = "CHANGE_ME"

  lifecycle {
    ignore_changes = [secret_string]
  }
}
