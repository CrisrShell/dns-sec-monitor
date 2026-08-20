#!/bin/bash
# Runs automatically on first boot, as root, before anyone logs in.
# Output goes to /var/log/cloud-init-output.log on the machine.
set -e

# --- Install Docker ---
dnf update -y
dnf install -y docker git
systemctl enable --now docker

# --- Install Docker Compose (v2 plugin) ---
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# --- Fetch the project and start the stack ---
cd /opt
git clone https://github.com/CrisrShell/dns-sec-monitor.git
cd dns-sec-monitor
docker compose up -d