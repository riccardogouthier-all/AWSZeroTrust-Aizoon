resource "aws_security_group" "host" {
  for_each    = local.hosts
  name        = "${var.project}-${each.key}"
  description = "Lab host ${each.key}"
  vpc_id      = aws_vpc.lab.id
}

# Internet -> WAF: solo HTTPS dai CIDR autorizzati.
resource "aws_vpc_security_group_ingress_rule" "https" {
  for_each          = var.tester_ipv4_cidrs
  description       = "HTTPS pubblico verso WAF"
  security_group_id = aws_security_group.host["waf"].id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

# WAF -> web (Juice Shop).
resource "aws_vpc_security_group_ingress_rule" "backend" {
  description                  = "WAF verso Juice Shop"
  security_group_id            = aws_security_group.host["web"].id
  referenced_security_group_id = aws_security_group.host["waf"].id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

resource "aws_vpc_security_group_egress_rule" "backend" {
  description                  = "WAF verso Juice Shop"
  security_group_id            = aws_security_group.host["waf"].id
  referenced_security_group_id = aws_security_group.host["web"].id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

# web e WAF -> SIEM (agent Wazuh).
resource "aws_vpc_security_group_ingress_rule" "agents" {
  for_each                     = toset(["web", "waf"])
  description                  = "Agent Wazuh ${each.key} verso SIEM"
  security_group_id            = aws_security_group.host["siem"].id
  referenced_security_group_id = aws_security_group.host[each.key].id
  ip_protocol                  = "tcp"
  from_port                    = 1514
  to_port                      = 1515
}

resource "aws_vpc_security_group_egress_rule" "agents" {
  for_each                     = toset(["web", "waf"])
  description                  = "Agent Wazuh ${each.key} verso SIEM"
  security_group_id            = aws_security_group.host[each.key].id
  referenced_security_group_id = aws_security_group.host["siem"].id
  ip_protocol                  = "tcp"
  from_port                    = 1514
  to_port                      = 1515
}

# Uscita verso Internet (pacchetti, immagini, SSM, CloudWatch) tramite NAT.
resource "aws_vpc_security_group_egress_rule" "https" {
  for_each          = local.hosts
  description       = "HTTPS in uscita"
  security_group_id = aws_security_group.host[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "http" {
  for_each          = local.hosts
  description       = "HTTP in uscita (apt)"
  security_group_id = aws_security_group.host[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}
