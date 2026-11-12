variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "project" {
  type    = string
  default = "aizoon-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project))
    error_message = "Usare da 3 a 25 caratteri: lettere minuscole, numeri e trattini."
  }
}

variable "tester_ipv4_cidrs" {
  description = "IP pubblici autorizzati al WAF, ad esempio [\"203.0.113.10/32\"]. Richiesto prima del plan."
  type        = set(string)
  validation {
    condition = length(var.tester_ipv4_cidrs) > 0 && alltrue([
      for cidr in var.tester_ipv4_cidrs :
      can(cidrnetmask(cidr)) && try(tonumber(split("/", cidr)[1]) >= 24, false)
    ])
    error_message = "Specificare almeno un CIDR IPv4 da /24 a /32; accesso globale non consentito."
  }
}

variable "github_repository" {
  description = "owner/repo per abilitare il ruolo CD; null finché repository e ambiente GitHub non sono concordati."
  type        = string
  default     = null
  validation {
    condition     = var.github_repository == null ? true : can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Usare owner/repo oppure null."
  }
}

variable "github_oidc_provider_arn" {
  description = "ARN del provider GitHub già presente nell'account; null per crearne uno quando CI/CD è abilitato."
  type        = string
  default     = null
}
