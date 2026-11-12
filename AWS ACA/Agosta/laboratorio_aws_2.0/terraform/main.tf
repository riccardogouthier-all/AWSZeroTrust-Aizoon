terraform {
  required_version = ">= 1.9, < 2"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {}
}

variable "region" { type = string }
variable "project" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project))
    error_message = "Project: 3-25 caratteri minuscoli, numeri e trattini."
  }
}
variable "instance_profile" { type = string }
variable "backup_role_name" {
  type    = string
  default = "LabRole"
}
variable "tester_ipv4_cidrs" {
  type = set(string)
  validation {
    condition = length(var.tester_ipv4_cidrs) > 0 && alltrue([
      for cidr in var.tester_ipv4_cidrs : can(cidrnetmask(cidr))
    ])
    error_message = "Inserire CIDR IPv4 validi. Il WAF pubblico è autorizzato per questa prova."
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, Environment = "private-test", ManagedBy = "Terraform" }
  }
}

data "aws_caller_identity" "current" {}
data "aws_iam_role" "lab" { name = var.backup_role_name }
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}
data "aws_availability_zones" "available" { state = "available" }

locals {
  logs_bucket = "${var.project}-logs-${data.aws_caller_identity.current.account_id}"
  hosts = {
    waf  = { type = "t3.small", disk = 20 }
    web  = { type = "t3.small", disk = 20 }
    siem = { type = "t3.large", disk = 50 }
  }
}

resource "aws_vpc" "lab" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.project }
}
resource "aws_default_security_group" "closed" { vpc_id = aws_vpc.lab.id }
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.lab.id
  cidr_block        = "10.20.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = { Name = "${var.project}-public" }
}
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.lab.id
  cidr_block        = "10.20.2.0/24"
  availability_zone = aws_subnet.public.availability_zone
  tags              = { Name = "${var.project}-private" }
}
resource "aws_internet_gateway" "lab" { vpc_id = aws_vpc.lab.id }
resource "aws_eip" "nat" { domain = "vpc" }
resource "aws_nat_gateway" "lab" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
  depends_on    = [aws_internet_gateway.lab]
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lab.id
  }
}
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.lab.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.lab.id
  }
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.lab.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id, aws_route_table.private.id]
}

resource "aws_security_group" "host" {
  description = "Private lab host access"
  for_each    = local.hosts
  name        = "${var.project}-${each.key}"
  vpc_id      = aws_vpc.lab.id
}
resource "aws_vpc_security_group_ingress_rule" "https" {
  description       = "Explicit private lab service flow"
  for_each          = var.tester_ipv4_cidrs
  security_group_id = aws_security_group.host["waf"].id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
resource "aws_vpc_security_group_ingress_rule" "backend" {
  description                  = "Explicit private lab service flow"
  security_group_id            = aws_security_group.host["web"].id
  referenced_security_group_id = aws_security_group.host["waf"].id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}
resource "aws_vpc_security_group_ingress_rule" "agents" {
  description                  = "Explicit private lab service flow"
  for_each                     = toset(["web", "waf"])
  security_group_id            = aws_security_group.host["siem"].id
  referenced_security_group_id = aws_security_group.host[each.key].id
  ip_protocol                  = "tcp"
  from_port                    = 1514
  to_port                      = 1515
}
resource "aws_vpc_security_group_egress_rule" "https" {
  description       = "Explicit private lab service flow"
  for_each          = local.hosts
  security_group_id = aws_security_group.host[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}
resource "aws_vpc_security_group_egress_rule" "http" {
  description       = "Explicit private lab service flow"
  for_each          = local.hosts
  security_group_id = aws_security_group.host[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}
resource "aws_vpc_security_group_egress_rule" "backend" {
  description                  = "Explicit private lab service flow"
  security_group_id            = aws_security_group.host["waf"].id
  referenced_security_group_id = aws_security_group.host["web"].id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}
resource "aws_vpc_security_group_egress_rule" "agents" {
  description                  = "Explicit private lab service flow"
  for_each                     = toset(["web", "waf"])
  security_group_id            = aws_security_group.host[each.key].id
  referenced_security_group_id = aws_security_group.host["siem"].id
  ip_protocol                  = "tcp"
  from_port                    = 1514
  to_port                      = 1515
}

# Il Learner Lab fornisce LabInstanceProfile: non si creano o modificano ruoli IAM.
resource "aws_instance" "host" {
  for_each                    = local.hosts
  ami                         = nonsensitive(data.aws_ssm_parameter.ubuntu.value)
  instance_type               = each.value.type
  subnet_id                   = each.key == "waf" ? aws_subnet.public.id : aws_subnet.private.id
  associate_public_ip_address = each.key == "waf"
  iam_instance_profile        = var.instance_profile
  vpc_security_group_ids      = [aws_security_group.host[each.key].id]
  monitoring                  = true
  ebs_optimized               = true
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = each.value.disk
    encrypted             = true
    delete_on_termination = true
  }
  tags       = { Name = "${var.project}-${each.key}", Role = each.key }
  depends_on = [aws_route_table_association.private, aws_route_table_association.public]
}
resource "aws_eip" "waf" {
  domain     = "vpc"
  instance   = aws_instance.host["waf"].id
  depends_on = [aws_internet_gateway.lab]
}

# Bucket creato tramite API S3 consentite: il Lab nega GetBucketObjectLockConfiguration richiesto da aws_s3_bucket.
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = local.logs_bucket
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = local.logs_bucket
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "logs" {
  bucket = local.logs_bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Sid = "TLSOnly", Effect = "Deny", Principal = "*", Action = "s3:*", Resource = ["arn:aws:s3:::${local.logs_bucket}", "arn:aws:s3:::${local.logs_bucket}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } },
      { Sid = "DeliveryAcl", Effect = "Allow", Principal = { Service = "delivery.logs.amazonaws.com" }, Action = "s3:GetBucketAcl", Resource = "arn:aws:s3:::${local.logs_bucket}", Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }, ArnLike = { "aws:SourceArn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*" } } },
      { Sid = "DeliveryWrite", Effect = "Allow", Principal = { Service = "delivery.logs.amazonaws.com" }, Action = "s3:PutObject", Resource = "arn:aws:s3:::${local.logs_bucket}/AWSLogs/${data.aws_caller_identity.current.account_id}/*", Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id, "s3:x-amz-acl" = "bucket-owner-full-control" }, ArnLike = { "aws:SourceArn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*" } } },
    ]
  })
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
}
resource "aws_flow_log" "lab" {
  vpc_id                   = aws_vpc.lab.id
  traffic_type             = "ALL"
  log_destination_type     = "s3"
  log_destination          = "arn:aws:s3:::${local.logs_bucket}"
  max_aggregation_interval = 60
  depends_on               = [aws_s3_bucket_policy.logs]
}

resource "aws_cloudwatch_log_group" "system" {
  name              = "/${var.project}/system"
  retention_in_days = 7
}
resource "aws_sns_topic" "alerts" { name = "${var.project}-alerts" }
resource "aws_sqs_queue" "alerts" {
  name                      = "${var.project}-alerts"
  sqs_managed_sse_enabled   = true
  message_retention_seconds = 86400
}
resource "aws_sqs_queue_policy" "alerts" {
  queue_url = aws_sqs_queue.alerts.url
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "sns.amazonaws.com" }, Action = "sqs:SendMessage", Resource = aws_sqs_queue.alerts.arn, Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.alerts.arn } } }]
  })
}
resource "aws_sns_topic_subscription" "alerts" {
  topic_arn  = aws_sns_topic.alerts.arn
  protocol   = "sqs"
  endpoint   = aws_sqs_queue.alerts.arn
  depends_on = [aws_sqs_queue_policy.alerts]
}
resource "aws_cloudwatch_metric_alarm" "memory" {
  for_each            = local.hosts
  alarm_name          = "${var.project}-${each.key}-memory"
  namespace           = "AizoonLab"
  metric_name         = "mem_used_percent"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  period              = 60
  statistic           = "Average"
  threshold           = 90
  dimensions          = { InstanceId = aws_instance.host[each.key].id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
resource "aws_cloudwatch_metric_alarm" "disk" {
  for_each            = local.hosts
  alarm_name          = "${var.project}-${each.key}-disk"
  namespace           = "AizoonLab"
  metric_name         = "disk_used_percent"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  period              = 60
  statistic           = "Average"
  threshold           = 85
  dimensions          = { InstanceId = aws_instance.host[each.key].id, path = "/", fstype = "ext4" }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
resource "aws_cloudwatch_metric_alarm" "https" {
  alarm_name          = "${var.project}-https"
  namespace           = "AizoonLab"
  metric_name         = "HTTPSAvailable"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"
  dimensions          = { Project = var.project }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
resource "aws_cloudwatch_metric_alarm" "cpu" {
  for_each            = local.hosts
  alarm_name          = "${var.project}-${each.key}-cpu"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  period              = 300
  statistic           = "Average"
  threshold           = 85
  dimensions          = { InstanceId = aws_instance.host[each.key].id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
resource "aws_cloudwatch_metric_alarm" "status" {
  for_each            = local.hosts
  alarm_name          = "${var.project}-${each.key}-status"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  dimensions          = { InstanceId = aws_instance.host[each.key].id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_backup_vault" "lab" {
  name          = "${var.project}-backup"
  force_destroy = false
}
resource "aws_backup_plan" "lab" {
  name = "${var.project}-daily"
  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.lab.name
    schedule          = "cron(0 2 * * ? *)"
    lifecycle { delete_after = 1 }
  }
}
resource "aws_backup_selection" "lab" {
  name         = "${var.project}-instances"
  plan_id      = aws_backup_plan.lab.id
  iam_role_arn = data.aws_iam_role.lab.arn
  resources    = [for host in aws_instance.host : host.arn]
}

output "instances" { value = { for role, host in aws_instance.host : role => { id = host.id, private_ip = host.private_ip, arn = host.arn, root_volume_id = host.root_block_device[0].volume_id } } }
output "waf_ip" { value = aws_eip.waf.public_ip }
output "vpc_id" { value = aws_vpc.lab.id }
output "private_subnet_id" { value = aws_subnet.private.id }
output "security_groups" { value = { for role, sg in aws_security_group.host : role => sg.id } }
output "logs_bucket" { value = local.logs_bucket }
output "backup_vault" { value = aws_backup_vault.lab.name }
output "alerts_topic" { value = aws_sns_topic.alerts.arn }
output "alerts_queue_url" { value = aws_sqs_queue.alerts.url }



output "region" { value = var.region }
output "project" { value = var.project }
output "instance_profile" { value = var.instance_profile }
output "backup_role_arn" { value = data.aws_iam_role.lab.arn }
output "ubuntu_ami_id" { value = nonsensitive(data.aws_ssm_parameter.ubuntu.value) }
