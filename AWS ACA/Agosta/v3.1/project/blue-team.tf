# Password iniziali create via API e conservate fuori dallo state Terraform.
resource "aws_iam_user" "blue" {
  name = "blue-team"
}

resource "aws_iam_group" "blue" {
  name = "BlueTeamLogs"
}

resource "aws_iam_user_group_membership" "blue" {
  user   = aws_iam_user.blue.name
  groups = [aws_iam_group.blue.name]
}

resource "aws_cloudwatch_log_group" "blue_sessions" {
  name              = "/${var.project}/blue-team-sessions"
  retention_in_days = 7
}

resource "aws_ssm_document" "blue_dashboard" {
  name            = "${var.project}-WazuhDashboard"
  document_type   = "Session"
  document_format = "JSON"
  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Blue Team: solo dashboard Wazuh locale sulla porta 443"
    sessionType   = "Port"
    parameters = {
      localPortNumber = { type = "String", default = "8443", allowedPattern = "^[0-9]{1,5}$" }
    }
    properties = {
      portNumber      = "443"
      type            = "LocalPortForwarding"
      localPortNumber = "{{ localPortNumber }}"
    }
  })
}

resource "aws_ssm_document" "blue_defence" {
  name            = "SessionDocument-${var.project}-BlueDefence"
  document_type   = "Session"
  document_format = "JSON"
  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Amministrazione Blue Team WAF/SIEM con registrazione CloudWatch"
    sessionType   = "Standard_Stream"
    inputs = {
      cloudWatchLogGroupName      = aws_cloudwatch_log_group.blue_sessions.name
      cloudWatchEncryptionEnabled = false
      cloudWatchStreamingEnabled  = true
      idleSessionTimeout          = "15"
      maxSessionDuration          = "60"
      runAsEnabled                = false
      shellProfile                = { linux = "", windows = "" }
    }
  })
}

resource "aws_iam_role" "blue_defence" {
  name                 = "${var.project}-BlueDefence"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { AWS = aws_iam_user.blue.arn }
      Condition = {
        Bool         = { "aws:MultiFactorAuthPresent" = "true" }
        StringEquals = { "sts:RoleSessionName" = ["blue-team", "blue-team-live"] }
      }
    }]
  })
}

resource "aws_iam_role_policy" "blue_defence" {
  name = "administer-waf-and-siem-sessions-only"
  role = aws_iam_role.blue_defence.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = "ssm:StartSession"
        Resource  = [aws_instance.host["waf"].arn, aws_instance.host["siem"].arn]
        Condition = { Bool = { "ssm:SessionDocumentAccessCheck" = "true" } }
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:StartSession", "ssm:GetDocument", "ssm:DescribeDocument"]
        Resource = aws_ssm_document.blue_defence.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:DescribeInstanceInformation", "ssm:DescribeInstanceProperties", "ssm:DescribeSessions",
          "ssm:GetConnectionStatus", "ssm:ListDocuments", "ec2:DescribeInstances", "ec2:DescribeInstanceStatus",
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:TerminateSession", "ssm:ResumeSession", "ssmmessages:OpenDataChannel"]
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:session/blue-team-*"
      },
    ]
  })
}

resource "aws_iam_policy" "blue" {
  name = "${var.project}-BlueTeamLogs"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DiscoverLogsAndMetrics"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups", "logs:GetQueryResults", "logs:StopQuery",
          "cloudwatch:ListMetrics", "cloudwatch:GetMetricData", "cloudwatch:GetMetricStatistics",
          "cloudwatch:DescribeAlarms", "cloudwatch:DescribeAlarmHistory", "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus", "ec2:DescribeFlowLogs", "ssm:DescribeInstanceInformation",
          "ssm:GetConnectionStatus", "s3:ListAllMyBuckets",
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadProjectLogContent"
        Effect = "Allow"
        Action = ["logs:DescribeLogStreams", "logs:GetLogEvents", "logs:FilterLogEvents", "logs:StartQuery", "logs:GetLogRecord"]
        Resource = [
          aws_cloudwatch_log_group.system.arn, "${aws_cloudwatch_log_group.system.arn}:*",
          aws_cloudwatch_log_group.blue_sessions.arn, "${aws_cloudwatch_log_group.blue_sessions.arn}:*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetBucketLocation", "s3:ListBucket"]
        Resource = "arn:aws:s3:::${local.logs_bucket}"
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "arn:aws:s3:::${local.logs_bucket}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
      },
      {
        Effect    = "Allow"
        Action    = "ssm:StartSession"
        Resource  = aws_instance.host["siem"].arn
        Condition = { BoolIfExists = { "ssm:SessionDocumentAccessCheck" = "true" } }
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:StartSession", "ssm:GetDocument", "ssm:DescribeDocument"]
        Resource = aws_ssm_document.blue_dashboard.arn
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:TerminateSession", "ssm:ResumeSession", "ssmmessages:OpenDataChannel"]
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:session/blue-team-*"
      },
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = aws_iam_role.blue_defence.arn
      },
      {
        Effect   = "Allow"
        Action   = ["signin:AuthorizeOAuth2Access", "signin:CreateOAuth2Token"]
        Resource = "arn:aws:signin:*:${data.aws_caller_identity.current.account_id}:oauth2/public-client/*"
      },
      {
        Sid      = "BootstrapOwnPasswordAndMFA"
        Effect   = "Allow"
        Action   = ["iam:GetUser", "iam:ChangePassword", "iam:GetLoginProfile", "iam:ListMFADevices", "iam:EnableMFADevice", "iam:ResyncMFADevice", "iam:DeactivateMFADevice"]
        Resource = aws_iam_user.blue.arn
      },
      {
        Effect   = "Allow"
        Action   = ["iam:CreateVirtualMFADevice", "iam:DeleteVirtualMFADevice"]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:mfa/blue-team*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:GetAccountPasswordPolicy", "iam:GetAccountSummary", "iam:ListVirtualMFADevices", "iam:ListAccountAliases", "sts:GetSessionToken"]
        Resource = "*"
      },
      {
        Sid    = "RequireMFABeforeReadingOrDefending"
        Effect = "Deny"
        NotAction = [
          "iam:GetUser", "iam:ChangePassword", "iam:GetLoginProfile", "iam:ListMFADevices",
          "iam:EnableMFADevice", "iam:ResyncMFADevice", "iam:CreateVirtualMFADevice", "iam:DeleteVirtualMFADevice",
          "iam:GetAccountPasswordPolicy", "iam:GetAccountSummary", "iam:ListVirtualMFADevices", "iam:ListAccountAliases", "sts:GetSessionToken",
        ]
        Resource  = "*"
        Condition = { BoolIfExists = { "aws:MultiFactorAuthPresent" = "false" } }
      },
    ]
  })
}

resource "aws_iam_group_policy_attachment" "blue" {
  group      = aws_iam_group.blue.name
  policy_arn = aws_iam_policy.blue.arn
}
