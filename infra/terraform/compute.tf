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
    cidr_blocks = ["0.0.0.0/0"] # NOTE: tighten to your own IP on real AWS
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
    cidr_blocks = ["0.0.0.0/0"] # NOTE: tighten on real AWS
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
  ami                    = "ami-0c02fb55956c7d316" # Amazon Linux 2 (us-east-1)
  instance_type          = "t2.micro"              # Free Tier eligible
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.monitor.id]

  # Startup script — runs on first boot via cloud-init. The machine configures
  # itself, so a rebuilt instance is identical without any manual setup.
  # NOTE: Floci stores user_data but cannot execute it — its emulated instances
  # are plain containers with no cloud-init. Verified only on real AWS.
  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "dns-monitor-host"
  }
}