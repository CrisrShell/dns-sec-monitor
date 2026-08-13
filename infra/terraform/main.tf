# ─── TERRAFORM & PROVIDER ─────────────────────────────────────────────────────
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# The AWS provider, pointed at Floci instead of real AWS.
# For the real deployment later: remove endpoints + the four provider-level
# dev settings below, and use real credentials. The resources stay IDENTICAL.
provider "aws" {
  region     = "us-east-1"
  access_key = "test"   # Floci accepts any non-empty value
  secret_key = "test"

  # Dev-only: don't validate against real AWS
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Use path-style S3 URLs (endpoint/bucket) instead of virtual-hosted-style
  # (bucket.endpoint) — Floci has no wildcard DNS to resolve the latter.
  s3_use_path_style = true

  endpoints {
    s3 = "http://localhost:4566"
  }
}

# ─── RESOURCES ────────────────────────────────────────────────────────────────
# First resource: an S3 bucket (cloud file storage).
# Trivial on purpose — today is about the workflow, not the resource.
resource "aws_s3_bucket" "artifacts" {
  bucket = "dns-monitor-artifacts"
}