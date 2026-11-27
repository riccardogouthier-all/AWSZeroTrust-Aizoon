resource "aws_cloudwatch_log_group" "system" {
  name              = "/${var.project}/system"
  retention_in_days = 7
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

resource "aws_sqs_queue" "alerts" {
  name                      = "${var.project}-alerts"
  sqs_managed_sse_enabled   = true
  message_retention_seconds = 86400
}

resource "aws_sqs_queue_policy" "alerts" {
  queue_url = aws_sqs_queue.alerts.url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.alerts.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.alerts.arn } }
    }]
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

# Snapshot ogni 6 ore per un RPO di 12 ore, con margine per la finestra di esecuzione.
resource "aws_backup_vault" "lab" {
  name          = "${var.project}-backup"
  force_destroy = false
}

resource "aws_backup_plan" "lab" {
  name = "${var.project}-daily"
  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.lab.name
    schedule          = "cron(0 2,8,14,20 * * ? *)"
    start_window      = 60
    completion_window = 180
    lifecycle { delete_after = 7 }
  }
}

resource "aws_backup_selection" "lab" {
  name         = "${var.project}-instances"
  plan_id      = aws_backup_plan.lab.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = [for host in aws_instance.host : host.arn]
}
