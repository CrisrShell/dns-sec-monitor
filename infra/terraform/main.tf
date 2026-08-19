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
    ec2 = "http://localhost:4566"
  }
}

# ─── RESOURCES ────────────────────────────────────────────────────────────────
# First resource: an S3 bucket (cloud file storage).
# Trivial on purpose — today is about the workflow, not the resource.
resource "aws_s3_bucket" "artifacts" {
  bucket = "dns-monitor-artifacts"
}

# ─── NETWORK ──────────────────────────────────────────────────────────────────
# The private network for the deployment — like renting a floor in a building.
# 10.0.0.0/16 gives us ~65,000 private addresses to hand out.
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "dns-monitor-vpc"
  }
}

# ─── SUBNET ───────────────────────────────────────────────────────────────────
# A slice of the network where our machine will live.
# 10.0.1.0/24 = 256 addresses, carved out of the /16 above.
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "dns-monitor-subnet"
  }
}

# ─── INTERNET ACCESS ──────────────────────────────────────────────────────────
# The doorway between our private network and the internet.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "dns-monitor-igw"
  }
}

# The signpost: "to reach anywhere on the internet (0.0.0.0/0), use the door."
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "dns-monitor-rt"
  }
}

# Attach the signpost to our room, so traffic there knows the way out.
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ─── FIREWALL ─────────────────────────────────────────────────────────────────
# Who's allowed in, and on which ports. Everything not listed is blocked.
resource "aws_security_group" "monitor" {
  name        = "dns-monitor-sg"
  description = "Access rules for the DNS monitor host"
  vpc_id      = aws_vpc.main.id

  # SSH — so you can log in and manage the machine
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # NOTE: tighten to your own IP on real AWS
  }

  # DNS — the whole point of the project
  ingress {
    description = "DNS (UDP)"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana dashboard
  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # NOTE: tighten on real AWS
  }

  # Outbound: allow everything (the machine needs to fetch Docker images etc.)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"          # -1 means "any protocol"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "dns-monitor-sg"
  }
}

# ─── THE MACHINE ──────────────────────────────────────────────────────────────
# The virtual computer that will run the docker-compose stack.
resource "aws_instance" "monitor" {
  ami                    = "ami-0c02fb55956c7d316"  # Amazon Linux 2 (us-east-1)
  instance_type          = "t2.micro"               # Free Tier eligible
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.monitor.id]

  tags = {
    Name = "dns-monitor-host"
  }
}