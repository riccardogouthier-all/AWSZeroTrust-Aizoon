# AMI Ubuntu 24.04 LTS ufficiale Canonical, letta dal parametro SSM pubblico.
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

# Nessun software installato qui: Docker, ModSecurity e Wazuh li configura Ansible.
resource "aws_instance" "role" {
  for_each = local.roles

  ami                         = nonsensitive(data.aws_ssm_parameter.ubuntu.value)
  instance_type               = var.instance_types[each.key]
  subnet_id                   = each.key == "waf" ? aws_subnet.public.id : aws_subnet.private.id
  associate_public_ip_address = false # il WAF riceve un Elastic IP dedicato
  vpc_security_group_ids      = [aws_security_group.role[each.key].id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  monitoring                  = true
  ebs_optimized               = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.disk_gb[each.key]
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name = "${var.project}-${each.key}"
    Role = each.key # usato dall'inventario dinamico Ansible
  }

  depends_on = [
    aws_route.private_default,
    aws_route.public_default,
    aws_iam_role_policy_attachment.ssm_core,
  ]
}

# IP pubblico stabile solo per il WAF.
resource "aws_eip" "waf" {
  domain   = "vpc"
  instance = aws_instance.role["waf"].id
  tags     = { Name = "${var.project}-waf-eip" }

  depends_on = [aws_internet_gateway.main]
}
