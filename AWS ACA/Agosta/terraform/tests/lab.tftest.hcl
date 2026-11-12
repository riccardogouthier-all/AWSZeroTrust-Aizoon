# Apply simulato: il mock provider non contatta AWS e non crea risorse.
mock_provider "aws" {
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/mock" }
  }
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:eu-west-1:123456789012:mock" }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:eu-west-1:123456789012:log-group:mock" }
  }
  mock_resource "aws_iam_openid_connect_provider" {
    defaults = { arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" }
  }
}

override_resource {
  target = aws_instance.host["web"]
  values = { arn = "arn:aws:ec2:eu-west-1:123456789012:instance/i-00000000000000001" }
}

override_resource {
  target = aws_instance.host["waf"]
  values = { arn = "arn:aws:ec2:eu-west-1:123456789012:instance/i-00000000000000002" }
}

override_resource {
  target = aws_instance.host["siem"]
  values = { arn = "arn:aws:ec2:eu-west-1:123456789012:instance/i-00000000000000003" }
}

override_data {
  target = data.aws_availability_zones.available
  values = { names = ["eu-west-1a"] }
}

override_data {
  target = data.aws_ami.ubuntu
  values = { id = "ami-0123456789abcdef0" }
}

variables {
  tester_ipv4_cidrs = ["203.0.113.10/32"]
}

run "isolated_lab" {
  command = apply
  assert {
    condition = (
      !aws_instance.host["web"].associate_public_ip_address &&
      !aws_instance.host["siem"].associate_public_ip_address &&
      aws_instance.host["waf"].associate_public_ip_address
    )
    error_message = "Solo il WAF deve ricevere un IP pubblico."
  }
  assert {
    condition     = alltrue([for host in aws_instance.host : host.metadata_options[0].http_tokens == "required" && host.root_block_device[0].encrypted])
    error_message = "Ogni VM richiede IMDSv2 e disco cifrato."
  }
  assert {
    condition     = length(aws_backup_selection.hosts.resources) == 3 && length(aws_cloudwatch_metric_alarm.status) == 3
    error_message = "Backup e allarmi devono coprire tutte e tre le VM."
  }
  assert {
    condition     = length(aws_iam_role.github_deploy) == 0
    error_message = "CI/CD deve restare disabilitato senza repository esplicito."
  }
}

run "reject_public_access" {
  command = plan
  variables {
    tester_ipv4_cidrs = ["0.0.0.0/0"]
  }
  expect_failures = [var.tester_ipv4_cidrs]
}

run "github_environment_trust" {
  command = apply
  variables {
    github_repository = "example/lab"
  }
  assert {
    condition     = jsondecode(aws_iam_role.github_deploy[0].assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == "repo:example/lab:environment:lab"
    error_message = "Il ruolo CD deve fidarsi solo dell'environment lab del repository indicato."
  }
}
