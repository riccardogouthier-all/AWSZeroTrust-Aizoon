data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  hosts = {
    web  = { instance_type = "t3.small", disk_gb = 20 }
    waf  = { instance_type = "t3.small", disk_gb = 20 }
    siem = { instance_type = "t3.large", disk_gb = 50 }
  }
}

resource "aws_iam_role" "host" {
  name = "${var.project}-ssm"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.host.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "host" {
  name = "${var.project}-ssm"
  role = aws_iam_role.host.name
}

# Solo hosting: Docker, Juice Shop, ModSecurity, TLS e Wazuh saranno configurati con Ansible.
# Il WAF deve usare TLS sulla porta 443; dashboard Wazuh accessibile tramite tunnel SSM.
resource "aws_instance" "host" {
  for_each                    = local.hosts
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = each.value.instance_type
  subnet_id                   = each.key == "waf" ? aws_subnet.public.id : aws_subnet.private.id
  associate_public_ip_address = each.key == "waf"
  vpc_security_group_ids      = [aws_security_group.host[each.key].id]
  iam_instance_profile        = aws_iam_instance_profile.host.name
  monitoring                  = true
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = each.value.disk_gb
    encrypted             = true
    delete_on_termination = true
  }
  tags = { Name = "${var.project}-${each.key}", Role = each.key }
  depends_on = [
    aws_iam_role_policy_attachment.ssm,
    aws_route_table_association.public,
    aws_route_table_association.private,
  ]
}
