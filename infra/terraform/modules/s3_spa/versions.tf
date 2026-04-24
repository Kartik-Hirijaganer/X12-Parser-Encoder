terraform {
  required_version = ">= 1.6.0"
  # provider_pin_repo_version = "1.0.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}
