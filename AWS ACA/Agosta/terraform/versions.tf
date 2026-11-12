terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "Terraform", Environment = "lab" }
  }
}

# Prima della CI condivisa configurare un backend remoto con locking.
# Nessuna credenziale deve essere inserita nei file Terraform o nel repository.
