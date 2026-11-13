terraform {
  required_version = ">= 1.9, < 2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State locale di default. Backend S3 opzionale (bucket creato a mano, con versioning):
  # backend "s3" {
  #   bucket       = "<bucket-tfstate>"
  #   key          = "lab/terraform.tfstate"
  #   region       = "us-east-1"
  #   use_lockfile = true
  #   encrypt      = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Environment = "private-test"
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_iam_role" "lab" { name = var.backup_role_name }
data "aws_availability_zones" "available" { state = "available" }

data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}
