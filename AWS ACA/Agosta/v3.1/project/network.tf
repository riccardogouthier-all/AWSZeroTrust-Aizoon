locals {
  logs_bucket = "${var.project}-logs-${data.aws_caller_identity.current.account_id}"

  # IP privati fissi: permettono di scrivere gli IP negli script user_data senza cicli di dipendenza.
  hosts = {
    waf  = { type = "t3.small", disk = 20, ip = "10.20.1.10" }
    web  = { type = "t3.small", disk = 20, ip = "10.20.2.10" }
    siem = { type = "m7i-flex.large", disk = 50, ip = "10.20.2.11" }
  }
}

resource "aws_vpc" "lab" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.project }
}

resource "aws_default_security_group" "closed" {
  vpc_id = aws_vpc.lab.id
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.lab.id
  cidr_block        = "10.20.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = { Name = "${var.project}-public" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.lab.id
  cidr_block        = "10.20.2.0/24"
  availability_zone = aws_subnet.public.availability_zone
  tags              = { Name = "${var.project}-private" }
}

resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
}

resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "lab" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
  depends_on    = [aws_internet_gateway.lab]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lab.id
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.lab.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.lab.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.lab.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id, aws_route_table.private.id]
}

# IP pubblico del WAF allocato prima dell'istanza: serve al certificato TLS generato in user_data.
resource "aws_eip" "waf" {
  domain     = "vpc"
  depends_on = [aws_internet_gateway.lab]
}

resource "aws_eip_association" "waf" {
  allocation_id = aws_eip.waf.id
  instance_id   = aws_instance.host["waf"].id
}
