# ─── FIREWALL ─────────────────────────────────────────────────────────────────
# Who's allowed in, and on which ports. Everything not listed is blocked.
resource "aws_security_group" "monitor" {
  name        = "dns-monitor-sg"
  description = "Access rules for the DNS monitor host"
  vpc_id      = aws_vpc.main.id

  # SSH — restricted to my current IP only
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  # DNS — the whole point of the project, open to anyone who wants to test it
  ingress {
    description = "DNS (UDP)"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana dashboard — restricted to my current IP only
  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  # Outbound: allow everything (the machine needs to fetch Docker images etc.)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # -1 means "any protocol"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "dns-monitor-sg"
  }
}

# ─── THE MACHINE ──────────────────────────────────────────────────────────────
# The virtual computer that will run the docker-compose stack.
resource "aws_instance" "monitor" {
  ami                         = "ami-081b0a6eac00b4f53" # Amazon Linux 2023
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.monitor.id]
  key_name                    = "dns-monitor-key"
  associate_public_ip_address = true

  # The default 8 GB root volume is too small: 4 GB goes to swap, and the
  # seven container images plus the engine build need ~6 GB more.
  # 30 GB is the Free Tier EBS allowance, so this costs nothing.
  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  # Startup script — runs on first boot via cloud-init. The machine configures
  # itself, so a rebuilt instance is identical without any manual setup.
  # NOTE: Floci stores user_data but cannot execute it — its emulated instances
  # are plain containers with no cloud-init. Verified only on real AWS.
  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "dns-monitor-host"
  }
}