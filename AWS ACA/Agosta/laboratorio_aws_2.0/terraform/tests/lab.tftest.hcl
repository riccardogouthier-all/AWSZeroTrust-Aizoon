mock_provider "aws" {
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:us-east-1:123456789012:test" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = { arn = "arn:aws:sqs:us-east-1:123456789012:test", url = "https://sqs.us-east-1.amazonaws.com/123456789012/test" }
  }
}

override_data {
  target = data.aws_caller_identity.current
  values = { account_id = "123456789012" }
}
override_data {
  target = data.aws_iam_role.lab
  values = { arn = "arn:aws:iam::123456789012:role/LabRole" }
}
override_data {
  target = data.aws_ssm_parameter.ubuntu
  values = { value = "ami-0123456789abcdef0" }
}
override_data {
  target = data.aws_availability_zones.available
  values = { names = ["us-east-1a"] }
}
override_resource {
  target = aws_instance.host["web"]
  values = { arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-00000000000000001" }
}
override_resource {
  target = aws_instance.host["waf"]
  values = { arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-00000000000000002" }
}
override_resource {
  target = aws_instance.host["siem"]
  values = { arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-00000000000000003" }
}

variables {
  region            = "us-east-1"
  project           = "replication-test"
  instance_profile  = "LabInstanceProfile"
  tester_ipv4_cidrs = ["0.0.0.0/0"]
}

run "public_waf_private_services" {
  command = apply
  assert {
    condition     = aws_instance.host["waf"].associate_public_ip_address && !aws_instance.host["web"].associate_public_ip_address && !aws_instance.host["siem"].associate_public_ip_address
    error_message = "Solo il WAF deve essere pubblico."
  }
  assert {
    condition     = length(aws_backup_selection.lab.resources) == 3 && length(aws_cloudwatch_metric_alarm.memory) == 3 && length(aws_cloudwatch_metric_alarm.disk) == 3
    error_message = "Backup e monitoring devono coprire le tre VM."
  }
  assert {
    condition     = alltrue([for host in aws_instance.host : host.root_block_device[0].encrypted && host.metadata_options[0].http_tokens == "required"])
    error_message = "Sono richiesti dischi cifrati e IMDSv2."
  }
}

run "reject_invalid_cidr" {
  command = plan
  variables { tester_ipv4_cidrs = ["not-a-cidr"] }
  expect_failures = [var.tester_ipv4_cidrs]
}
