resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

# Collegare un destinatario al topic prima delle prove operative.
resource "aws_cloudwatch_metric_alarm" "cpu" {
  for_each            = aws_instance.host
  alarm_name          = "${var.project}-${each.key}-cpu"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 85
  treat_missing_data  = "missing"
  dimensions          = { InstanceId = each.value.id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "status" {
  for_each            = aws_instance.host
  alarm_name          = "${var.project}-${each.key}-status"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "missing"
  dimensions          = { InstanceId = each.value.id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# I Flow Logs descrivono le connessioni; i log applicativi e WAF richiedono gli agent Wazuh.
resource "aws_cloudwatch_log_group" "flow" {
  name              = "/${var.project}/vpc-flow"
  retention_in_days = 14
}

resource "aws_iam_role" "flow" {
  name = "${var.project}-flow-logs"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "vpc-flow-logs.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "flow" {
  role = aws_iam_role.flow.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
        Resource = "${aws_cloudwatch_log_group.flow.arn}:*"
      },
      { Effect = "Allow", Action = "logs:DescribeLogGroups", Resource = "*" },
    ]
  })
}

resource "aws_flow_log" "lab" {
  iam_role_arn    = aws_iam_role.flow.arn
  log_destination = aws_cloudwatch_log_group.flow.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.lab.id
  depends_on      = [aws_iam_role_policy.flow]
}
