# syntax=docker/dockerfile:1.7

# ─── STAGE 1: BUILDER ─────────────────────────────────────────────────────────
# Heavier image with compilers to build dependencies.
# This stage is thrown away after building.
FROM python:3.12-slim AS builder

# Install build tools needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the dependency manifest first.
# This is cached if pyproject.toml does not change — fast rebuilds.
COPY pyproject.toml ./

# Install dependencies into an isolated path we can copy to stage 2
RUN pip install --no-cache-dir --prefix=/install pandas elasticsearch prometheus-client

# ─── STAGE 2: RUNTIME ─────────────────────────────────────────────────────────
# Lean image — only Python runtime, no build tools.
FROM python:3.12-slim AS runtime

# Create non-root user for security — never run containers as root in production
RUN groupadd --system dnsmonitor && \
    useradd --system --gid dnsmonitor --create-home dnsmonitor

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Set working directory
WORKDIR /app

# Copy application code with correct ownership
COPY --chown=dnsmonitor:dnsmonitor src/ ./src/

# Tell Python where to find our package
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default environment variables (can be overridden at runtime)
ENV ZEEK_LOG=/logs/dns.log \
    CSV_OUT=/data/dns_security_report.csv \
    HTML_OUT=/data/dns_dashboard.html \
    ES_HOST=https://elasticsearch:9200 \
    ES_INDEX=dns-alerts \
    ENTROPY_LIMIT=4.0 \
    LENGTH_LIMIT=50 \
    ZSCORE_LIMIT=3.0

# Create data directory and give ownership to non-root user
RUN mkdir -p /data /logs && \
    chown -R dnsmonitor:dnsmonitor /data /logs

# Expose the Prometheus metrics port
EXPOSE 9100

# Switch to non-root user — security best practice
USER dnsmonitor

# Run the engine
CMD ["python", "-m", "dns_monitor"]