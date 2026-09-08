#!/bin/bash
# Runs automatically on first boot, as root, before anyone logs in.
# Output goes to /var/log/cloud-init-output.log on the machine.
set -e

# --- Create Swap Space (Virtual RAM) ---
dd if=/dev/zero of=/swapfile bs=1M count=4096
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# --- Install Docker ---
dnf update -y
dnf install -y docker git
systemctl enable --now docker

# --- Install Docker CLI Plugins (Compose and Buildx) ---
mkdir -p /usr/local/lib/docker/cli-plugins

# Deterministic Versioning for Production Stability
# 1. Install Docker Compose v2.29.2
curl -SL https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 2. Install Docker Buildx v0.19.1 (satisfies >= 0.17.0 requirement)
curl -SL https://github.com/docker/buildx/releases/download/v0.19.1/buildx-v0.19.1.linux-amd64 \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

# --- Fetch the project and start the stack ---
cd /opt
git clone https://github.com/CrisrShell/dns-sec-monitor.git
cd dns-sec-monitor
docker compose up -d