locals {
  # Variabili comuni esportate in testa a ogni script. Nessun segreto qui.
  common_env = {
    PROJECT      = var.project
    REGION       = var.region
    WAF_PUBLIC   = aws_eip.waf.public_ip
    WAF_PRIVATE  = local.hosts.waf.ip
    WEB_PRIVATE  = local.hosts.web.ip
    SIEM_PRIVATE = local.hosts.siem.ip
    JUICE_IMAGE  = var.juice_shop_image
    WAF_IMAGE    = var.waf_image
    WAZUH_SERIES = var.wazuh_series
  }

  # Script per ruolo = intestazione env + common.sh + ruolo.sh + [waf-health.sh] + [agent.sh]
  # L'agent va per ultimo: attende il SIEM, che impiega molti minuti.
  user_data = {
    for role in keys(local.hosts) : role => join("\n", concat(
      ["#!/bin/bash", "export ROLE=${role}"],
      [for k, v in local.common_env : "export ${k}='${v}'"],
      [file("${path.module}/scripts/common.sh")],
      [file("${path.module}/scripts/${role}.sh")],
      role == "waf" ? [file("${path.module}/scripts/waf-health.sh")] : [],
      role == "siem" ? [] : [file("${path.module}/scripts/agent.sh")],
    ))
  }
}

# Il Learner Lab fornisce LabInstanceProfile: nessun ruolo IAM creato o modificato.
resource "aws_instance" "host" {
  for_each                    = local.hosts
  ami                         = nonsensitive(data.aws_ssm_parameter.ubuntu.value)
  instance_type               = each.value.type
  subnet_id                   = each.key == "waf" ? aws_subnet.public.id : aws_subnet.private.id
  private_ip                  = each.value.ip
  associate_public_ip_address = each.key == "waf"
  iam_instance_profile        = var.instance_profile
  vpc_security_group_ids      = [aws_security_group.host[each.key].id]
  monitoring                  = true
  ebs_optimized               = true

  user_data_base64            = base64gzip(local.user_data[each.key])
  user_data_replace_on_change = true

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

  tags = { Name = "${var.project}-${each.key}", Role = each.key }

  depends_on = [
    aws_route_table_association.private,
    aws_route_table_association.public,
    aws_nat_gateway.lab,
  ]
}
