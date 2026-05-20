# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
# Environment variables override these defaults. Allows configuration without
# code changes — follows the 12-factor app methodology.

from __future__ import annotations

import os

# File Paths
ZEEK_LOG: str = os.getenv("ZEEK_LOG", "/opt/zeek/logs/current/dns.log")
CSV_OUT: str = os.getenv("CSV_OUT", os.path.expanduser("~/dns_security_report.csv"))
HTML_OUT: str = os.getenv("HTML_OUT", os.path.expanduser("~/dns_dashboard.html"))

# Detection thresholds
ENTROPY_LIMIT: float = float(os.getenv("ENTROPY_LIMIT", "4.0"))
LENGTH_LIMIT: int = int(os.getenv("LENGTH_LIMIT", "50"))
ZSCORE_LIMIT: float = float(os.getenv("ZSCORE_LIMIT", "3.0"))
FREQ_WINDOW: int = int(os.getenv("FREQ_WINDOW", "50"))
MIN_HISTORY: int = int(os.getenv("MIN_HISTORY", "10"))

# Elasticsearch
ES_HOST: str = os.getenv("ES_HOST", "https://localhost:9200")
ES_USER: str = os.getenv("ES_USER", "elastic")
ES_PASS: str = os.getenv("ES_PASS", "")
ES_INDEX: str = os.getenv("ES_INDEX", "dns-alerts")
