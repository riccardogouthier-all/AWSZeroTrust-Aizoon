variable "region" {
  description = "Regione AWS."
  type        = string
  default     = "eu-west-1"
}

variable "project" {
  description = "Prefisso per nomi e tag."
  type        = string
  default     = "lab-integrato"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project))
    error_message = "3-25 caratteri: minuscole, numeri, trattini; inizia con una lettera."
  }
}

variable "environment" {
  description = "Nome ambiente (solo tag)."
  type        = string
  default     = "lab"
}

variable "allowed_cidrs" {
  description = "CIDR IPv4 autorizzati a raggiungere il WAF su 443 (es. [\"203.0.113.10/32\"]). Obbligatorio."
  type        = list(string)
  validation {
    condition = length(var.allowed_cidrs) > 0 && alltrue([
      for c in var.allowed_cidrs :
      can(cidrnetmask(c)) && tonumber(split("/", c)[1]) >= 24
    ])
    error_message = "Almeno un CIDR valido con prefisso /24../32. 0.0.0.0/0 non ammesso."
  }
}

variable "vpc_cidr" {
  description = "CIDR della VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  type    = string
  default = "10.20.1.0/24"
}

variable "private_subnet_cidr" {
  type    = string
  default = "10.20.2.0/24"
}

variable "instance_types" {
  description = "Tipo istanza per ruolo."
  type        = map(string)
  default = {
    web  = "t3.small"
    waf  = "t3.small"
    siem = "t3.large" # Wazuh all-in-one: minimo 4 vCPU/8 GB consigliati
  }
}

variable "disk_gb" {
  description = "Dimensione disco root (GiB) per ruolo."
  type        = map(number)
  default = {
    web  = 20
    waf  = 20
    siem = 50
  }
}

variable "flow_logs_retention_days" {
  description = "Retention dei VPC Flow Logs in CloudWatch."
  type        = number
  default     = 30
}

variable "budget_email" {
  description = "Email per alert budget. null = budget non creato."
  type        = string
  default     = null
}

variable "budget_usd" {
  description = "Soglia mensile in USD per l'alert budget."
  type        = number
  default     = 80
}
