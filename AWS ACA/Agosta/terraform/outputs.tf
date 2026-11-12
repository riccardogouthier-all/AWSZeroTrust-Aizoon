output "instances" {
  value = { for role, host in aws_instance.host : role => {
    id = host.id, private_ip = host.private_ip, public_ip = host.public_ip
  } }
}

output "waf_https_endpoint" {
  description = "Utilizzabile solo dopo configurazione reverse proxy e TLS; IP non statico."
  value       = "https://${aws_instance.host["waf"].public_ip}"
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "backup_vault_name" {
  value = aws_backup_vault.lab.name
}

output "github_deploy_role_arn" {
  value = try(aws_iam_role.github_deploy[0].arn, null)
}

# QA: test funzionali, cross-browser e mobile richiedono applicazione configurata e ambiente attivo.
# Nessun test browser o installazione software viene eseguito da questo Terraform.
