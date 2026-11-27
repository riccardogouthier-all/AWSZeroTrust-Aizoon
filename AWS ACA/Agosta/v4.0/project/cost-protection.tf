# Budget al lordo dei crediti: lo stop deve scattare anche con fattura netta pari a zero.
resource "aws_budgets_budget" "safety" {
  name         = "${var.project}-cost-budget"
  budget_type  = "COST"
  limit_amount = "20.0"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_types {
    include_credit = false
    include_refund = false
    use_blended    = false
  }
}

resource "aws_iam_role" "budget_stop" {
  name = "${var.project}-budget-stop"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "budgets.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnEquals    = { "aws:SourceArn" = aws_budgets_budget.safety.arn }
      }
    }]
  })
}

resource "aws_iam_role_policy" "budget_stop" {
  name = "stop-project-instances-via-ssm"
  role = aws_iam_role.budget_stop.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ec2:StopInstances"
        Resource = [for host in aws_instance.host : host.arn]
        Condition = {
          "ForAnyValue:StringEquals" = { "aws:CalledVia" = ["ssm.amazonaws.com"] }
        }
      },
      {
        Effect   = "Allow"
        Action   = "ec2:DescribeInstanceStatus"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "ssm:StartAutomationExecution"
        Resource = [
          "arn:aws:ssm:${var.region}::document/AWS-StopEC2Instance",
          "arn:aws:ssm:${var.region}::automation-definition/AWS-StopEC2Instance:*",
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:automation-execution/*",
        ]
      },
    ]
  })
}

resource "aws_sns_topic_policy" "budget_notifications" {
  arn = aws_sns_topic.alerts.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Mantiene la policy predefinita del topic, usata anche dagli allarmi esistenti.
      {
        Sid       = "DefaultOwnerAccess"
        Effect    = "Allow"
        Principal = { AWS = "*" }
        Action = [
          "SNS:GetTopicAttributes", "SNS:SetTopicAttributes", "SNS:AddPermission",
          "SNS:RemovePermission", "SNS:DeleteTopic", "SNS:Subscribe",
          "SNS:ListSubscriptionsByTopic", "SNS:Publish",
        ]
        Resource  = aws_sns_topic.alerts.arn
        Condition = { StringEquals = { "AWS:SourceOwner" = data.aws_caller_identity.current.account_id } }
      },
      {
        Sid       = "BudgetNotifications"
        Effect    = "Allow"
        Principal = { Service = "budgets.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.alerts.arn
        Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
      },
    ]
  })
}

resource "aws_budgets_budget_action" "stop_ec2" {
  budget_name        = aws_budgets_budget.safety.name
  action_type        = "RUN_SSM_DOCUMENTS"
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.budget_stop.arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 100
  }
  definition {
    ssm_action_definition {
      action_sub_type = "STOP_EC2_INSTANCES"
      region          = var.region
      instance_ids    = [for host in aws_instance.host : host.id]
    }
  }
  subscriber {
    subscription_type = "SNS"
    address           = aws_sns_topic.alerts.arn
  }
  depends_on = [aws_iam_role_policy.budget_stop, aws_sns_topic_policy.budget_notifications]
}
