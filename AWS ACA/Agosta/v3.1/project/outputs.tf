output "waf_ip" {
  description = "IP pubblico del WAF: https://<waf_ip>"
  value       = aws_eip.waf.public_ip
}

output "instances" {
  value = { for role, host in aws_instance.host : role => { id = host.id, private_ip = host.private_ip } }
}

output "logs_bucket" {
  value = local.logs_bucket
}

output "backup_vault" {
  value = aws_backup_vault.lab.name
}

output "alerts_topic" {
  value = aws_sns_topic.alerts.arn
}

output "alerts_queue_url" {
  value = aws_sqs_queue.alerts.url
}

output "ssm_siem_tunnel" {
  description = "Port forwarding verso la dashboard Wazuh (poi https://localhost:8443)."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.host["siem"].id} --document-name AWS-StartPortForwardingSession --parameters portNumber=443,localPortNumber=8443"
}

output "account_id" { value = data.aws_caller_identity.current.account_id }
output "region" { value = var.region }
output "project" { value = var.project }
