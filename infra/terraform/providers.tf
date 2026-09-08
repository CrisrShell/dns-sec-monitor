# ─── TERRAFORM & PROVIDER ─────────────────────────────────────────────────────
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# The AWS provider, targeting REAL AWS.
# Credentials come from the environment (AWS_ACCESS_KEY_ID,
# AWS_SECRET_ACCESS_KEY) — never written here. See SECRETS_AND_VERSION_CONTROL.md.
#
# Floci version of this file used a local endpoint and dummy credentials for
# free, offline development; this is the promoted version for the real
# deployment.
provider "aws" {
  region = "us-east-1"
}