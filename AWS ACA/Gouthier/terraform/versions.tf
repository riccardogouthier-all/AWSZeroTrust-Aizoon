terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Backend remoto opzionale (bucket S3 creato a mano, con versioning):
  # backend "s3" {
  #   bucket       = "<bucket-tfstate>"
  #   key          = "lab-integrato/terraform.tfstate"
  #   region       = "eu-west-1"
  #   use_lockfile = true
  #   encrypt      = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
      Purpose     = "lab-didattico"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
