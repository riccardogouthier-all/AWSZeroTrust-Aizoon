locals {
  roles = toset(["web", "waf", "siem"])
}

resource "aws_security_group" "role" {
  for_each    = local.roles
  name        = "${var.project}-${each.key}"
  description = "SG ruolo ${each.key}; amministrazione solo via SSM"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project}-${each.key}-sg" }
}

# ---------- INGRESS ----------
# Internet (solo IP autorizzati) -> WAF :443
resource "aws_vpc_security_group_ingress_rule" "waf_https" {
  for_each          = toset(var.allowed_cidrs)
  security_group_id = aws_security_group.role["waf"].id
  description       = "HTTPS dai tester"
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

# WAF -> Juice Shop :3000
resource "aws_vpc_security_group_ingress_rule" "web_from_waf" {
  security_group_id            = aws_security_group.role["web"].id
  description                  = "Proxy WAF verso Juice Shop"
  referenced_security_group_id = aws_security_group.role["waf"].id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

# Agent Wazuh (web, waf) -> SIEM :1514 (eventi) e :1515 (enrollment)
resource "aws_vpc_security_group_ingress_rule" "siem_agents" {
  for_each = {
    for p in setproduct(["web", "waf"], [1514, 1515]) : "${p[0]}-${p[1]}" => { src = p[0], port = p[1] }
  }
  security_group_id            = aws_security_group.role["siem"].id
  description                  = "Wazuh agent ${each.value.src} porta ${each.value.port}"
  referenced_security_group_id = aws_security_group.role[each.value.src].id
  ip_protocol                  = "tcp"
  from_port                    = each.value.port
  to_port                      = each.value.port
}

# ---------- EGRESS ----------
# Tutte le istanze: pacchetti, immagini Docker, regole CRS, SSM (80/443 verso NAT/IGW).
resource "aws_vpc_security_group_egress_rule" "web_out" {
  for_each          = toset(["80", "443"])
  security_group_id = aws_security_group.role["web"].id
  description       = "Uscita ${each.key}"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
}

resource "aws_vpc_security_group_egress_rule" "waf_out" {
  for_each          = toset(["80", "443"])
  security_group_id = aws_security_group.role["waf"].id
  description       = "Uscita ${each.key}"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
}

resource "aws_vpc_security_group_egress_rule" "siem_out" {
  for_each          = toset(["80", "443"])
  security_group_id = aws_security_group.role["siem"].id
  description       = "Uscita ${each.key}"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
}

resource "aws_vpc_security_group_egress_rule" "waf_to_web" {
  security_group_id            = aws_security_group.role["waf"].id
  description                  = "WAF verso Juice Shop"
  referenced_security_group_id = aws_security_group.role["web"].id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

resource "aws_vpc_security_group_egress_rule" "agents_to_siem" {
  for_each = {
    for p in setproduct(["web", "waf"], [1514, 1515]) : "${p[0]}-${p[1]}" => { src = p[0], port = p[1] }
  }
  security_group_id            = aws_security_group.role[each.value.src].id
  description                  = "Agent Wazuh verso SIEM ${each.value.port}"
  referenced_security_group_id = aws_security_group.role["siem"].id
  ip_protocol                  = "tcp"
  from_port                    = each.value.port
  to_port                      = each.value.port
}

# ---------- IAM per le istanze ----------
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2" {
  name               = "${var.project}-ec2"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Il plugin Ansible aws_ssm usa il bucket come area di scambio file.
data "aws_iam_policy_document" "ansible_bucket" {
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.ansible.arn]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.ansible.arn}/*"]
  }
}

resource "aws_iam_role_policy" "ansible_bucket" {
  name   = "bucket-ansible"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.ansible_bucket.json
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project}-ec2"
  role = aws_iam_role.ec2.name
}
