# Learner Lab nega GetBucketObjectLockConfiguration, letta da aws_s3_bucket: il bucket si crea via AWS CLI.
# Serve AWS CLI v2 nel PATH con le stesse credenziali usate da Terraform.
resource "terraform_data" "logs_bucket" {
  count = var.logs_bucket_via_cli ? 1 : 0

  input = {
    bucket = local.logs_bucket
    region = var.region
  }

  provisioner "local-exec" {
    command = "aws s3api create-bucket --bucket ${local.logs_bucket} --region ${var.region}${var.region == "us-east-1" ? "" : " --create-bucket-configuration LocationConstraint=${var.region}"}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "aws s3 rb s3://${self.input.bucket} --force --region ${self.input.region}"
  }
}

resource "aws_s3_bucket" "logs" {
  count         = var.logs_bucket_via_cli ? 0 : 1
  bucket        = local.logs_bucket
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = local.logs_bucket
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
  depends_on              = [terraform_data.logs_bucket, aws_s3_bucket.logs]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = local.logs_bucket
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
  depends_on = [terraform_data.logs_bucket, aws_s3_bucket.logs]
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = local.logs_bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "TLSOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = ["arn:aws:s3:::${local.logs_bucket}", "arn:aws:s3:::${local.logs_bucket}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "DeliveryAcl"
        Effect    = "Allow"
        Principal = { Service = "delivery.logs.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = "arn:aws:s3:::${local.logs_bucket}"
        Condition = {
          StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
          ArnLike      = { "aws:SourceArn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*" }
        }
      },
      {
        Sid       = "DeliveryWrite"
        Effect    = "Allow"
        Principal = { Service = "delivery.logs.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "arn:aws:s3:::${local.logs_bucket}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            "s3:x-amz-acl"      = "bucket-owner-full-control"
          }
          ArnLike = { "aws:SourceArn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*" }
        }
      },
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.logs]
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = local.logs_bucket
  rule {
    id     = "expire-private-test"
    status = "Enabled"
    filter {}
    expiration { days = 7 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
  depends_on = [terraform_data.logs_bucket, aws_s3_bucket.logs]
}

resource "aws_flow_log" "lab" {
  vpc_id                   = aws_vpc.lab.id
  traffic_type             = "ALL"
  log_destination_type     = "s3"
  log_destination          = "arn:aws:s3:::${local.logs_bucket}"
  max_aggregation_interval = 60
  depends_on               = [aws_s3_bucket_policy.logs]
}
