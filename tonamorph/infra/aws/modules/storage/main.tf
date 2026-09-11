resource "aws_s3_bucket" "jobs" {
  bucket = "${var.name}-jobs-${var.account_id}"
}

resource "aws_s3_bucket_public_access_block" "jobs" {
  bucket = aws_s3_bucket.jobs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "jobs" {
  bucket = aws_s3_bucket.jobs.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "jobs" {
  bucket = aws_s3_bucket.jobs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Job assets are valid for 24 h (contract §2 `expires_at`); S3 expires them the
# next day and abandoned multipart uploads are dropped just as quickly.
resource "aws_s3_bucket_lifecycle_configuration" "jobs" {
  bucket = aws_s3_bucket.jobs.id

  rule {
    id     = "expire-job-assets"
    status = "Enabled"

    filter {
      prefix = "jobs/"
    }

    expiration {
      days = 1
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

data "aws_iam_policy_document" "bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.jobs.arn,
      "${aws_s3_bucket.jobs.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  dynamic "statement" {
    for_each = var.enable_cloudfront ? [1] : []

    content {
      sid       = "AllowCloudFrontOriginAccessControl"
      effect    = "Allow"
      actions   = ["s3:GetObject"]
      resources = ["${aws_s3_bucket.jobs.arn}/*"]

      principals {
        type        = "Service"
        identifiers = ["cloudfront.amazonaws.com"]
      }

      condition {
        test     = "StringEquals"
        variable = "AWS:SourceArn"
        values   = [aws_cloudfront_distribution.jobs[0].arn]
      }
    }
  }
}

resource "aws_s3_bucket_policy" "jobs" {
  bucket = aws_s3_bucket.jobs.id
  policy = data.aws_iam_policy_document.bucket.json

  depends_on = [aws_s3_bucket_public_access_block.jobs]
}

# ---------------------------------------------------------------------------
# Optional CloudFront distribution: OAC to the bucket, signed URLs only
# ---------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "jobs" {
  count = var.enable_cloudfront ? 1 : 0

  name                              = "${var.name}-jobs"
  description                       = "OAC for the ${var.name} job asset bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_public_key" "signing" {
  count = var.enable_cloudfront ? 1 : 0

  name        = "${var.name}-jobs-signing"
  comment     = "Trusted key for ${var.name} signed asset URLs"
  encoded_key = var.cloudfront_public_key_pem

  lifecycle {
    precondition {
      condition     = var.cloudfront_public_key_pem != ""
      error_message = "cloudfront_public_key_pem is required when enable_cloudfront is true."
    }
  }
}

resource "aws_cloudfront_key_group" "signing" {
  count = var.enable_cloudfront ? 1 : 0

  name    = "${var.name}-jobs-signing"
  comment = "Keys allowed to sign ${var.name} asset URLs"
  items   = [aws_cloudfront_public_key.signing[0].id]
}

resource "aws_cloudfront_distribution" "jobs" {
  count = var.enable_cloudfront ? 1 : 0

  enabled         = true
  comment         = "${var.name} job assets"
  price_class     = "PriceClass_100"
  http_version    = "http2and3"
  is_ipv6_enabled = true

  origin {
    origin_id                = "s3-jobs"
    domain_name              = aws_s3_bucket.jobs.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.jobs[0].id
  }

  default_cache_behavior {
    target_origin_id       = "s3-jobs"
    viewer_protocol_policy = "https-only"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = false
    trusted_key_groups     = [aws_cloudfront_key_group.signing[0].id]

    # AWS managed "CachingOptimized" policy.
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1"
  }
}
