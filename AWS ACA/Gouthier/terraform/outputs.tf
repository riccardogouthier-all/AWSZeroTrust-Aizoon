output "waf_public_ip" {
  description = "IP pubblico del WAF (unico punto di ingresso)."
  value       = aws_eip.waf.public_ip
}

output "instance_ids" {
  description = "ID istanze per ruolo."
  value       = { for k, i in aws_instance.role : k => i.id }
}

output "private_ips" {
  description = "IP privati per ruolo (utili per upstream nginx e agent Wazuh)."
  value       = { for k, i in aws_instance.role : k => i.private_ip }
}

output "ansible_bucket" {
  description = "Bucket per ansible_aws_ssm_bucket_name."
  value       = aws_s3_bucket.ansible.id
}

output "ssm_shell_commands" {
  description = "Shell sulle istanze via SSM."
  value       = { for k, i in aws_instance.role : k => "aws ssm start-session --region ${var.region} --target ${i.id}" }
}

output "ssm_wazuh_dashboard_tunnel" {
  description = "Port-forward della dashboard Wazuh su https://localhost:8443."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.role["siem"].id} --document-name AWS-StartPortForwardingSession --parameters portNumber=443,localPortNumber=8443"
}
