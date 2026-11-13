variable "region" {
  description = "Regione AWS."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Nome progetto: prefisso di risorse e bucket."
  type        = string
  default     = "lab-integrato-v2"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project))
    error_message = "Project: 3-25 caratteri minuscoli, numeri e trattini."
  }
}

variable "instance_profile" {
  description = "Instance profile EC2 esistente (Learner Lab: LabInstanceProfile). Non vengono creati ruoli IAM."
  type        = string
  default     = "LabInstanceProfile"
}

variable "backup_role_name" {
  description = "Ruolo IAM esistente usato da AWS Backup."
  type        = string
  default     = "LabRole"
}

variable "tester_ipv4_cidrs" {
  description = "CIDR IPv4 autorizzati a raggiungere HTTPS (443) del WAF. 0.0.0.0/0 = pubblico."
  type        = set(string)

  validation {
    condition = length(var.tester_ipv4_cidrs) > 0 && alltrue([
      for cidr in var.tester_ipv4_cidrs : can(cidrnetmask(cidr))
    ])
    error_message = "Inserire CIDR IPv4 validi."
  }
}

variable "logs_bucket_via_cli" {
  description = "true: il bucket log viene creato con AWS CLI (terraform_data), perche' il Learner Lab nega GetBucketObjectLockConfiguration letta da aws_s3_bucket. false: usa aws_s3_bucket."
  type        = bool
  default     = true
}

variable "juice_shop_image" {
  description = "Immagine Juice Shop (riferimento con digest)."
  type        = string
  default     = "bkimminich/juice-shop@sha256:877fc77b12d72b42e486eb09b6b1711cc56514306d92006b284e7e7cf076a809"
}

variable "waf_image" {
  description = "Immagine nginx + ModSecurity + OWASP CRS (riferimento con digest)."
  type        = string
  default     = "owasp/modsecurity-crs@sha256:9a386aa4a9eeec9a46c61a1eaba101c846dd83b1ec125e9126e710dd61d84422"
}

variable "wazuh_series" {
  description = "Serie Wazuh (installer e agent)."
  type        = string
  default     = "4.14"
}
