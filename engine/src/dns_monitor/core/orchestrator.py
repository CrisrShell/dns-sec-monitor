"""Top-level orchestrator — coordinates ingestion, detection, and reporting."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from prometheus_client import Counter, start_http_server

from dns_monitor.config import ZEEK_LOG
from dns_monitor.core.record import DNSRecord
from dns_monitor.detection.engine import DetectionEngine
from dns_monitor.ingestion.log_reader import LogReader
from dns_monitor.reporting.shipper import AlertShipper

logger = logging.getLogger("dns_monitor")

# Prometheus metrics — module-level so they persist across the loop
QUERIES_PROCESSED = Counter(
    "dns_queries_processed_total",
    "Total DNS queries the engine has processed",
)
ALERTS_FIRED = Counter(
    "dns_alerts_fired_total",
    "Total alerts the engine has raised",
)


class DNSEngine:
    """Coordinates the LogReader → DetectionEngine → AlertShipper pipeline."""

    def __init__(self) -> None:
        self._reader: LogReader = LogReader(ZEEK_LOG)
        self._detector: DetectionEngine = DetectionEngine()
        self._shipper: AlertShipper = AlertShipper()

    def run(self) -> None:
        """Run the monitoring loop indefinitely."""
        start_http_server(9100)  # Expose /metrics on port 9100 for Prometheus
        for raw_line in self._reader.tail():
            data = self._reader.parse_line(raw_line)
            if not data:
                continue  # NFR4 — silently skip malformed input

            QUERIES_PROCESSED.inc()  # Count every valid query

            record = DNSRecord(
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                source_ip=data.get("id.orig_h"),
                query_string=data.get("query", "unknown"),
                rcode=data.get("rcode_name", "NONE"),
                query_type=data.get("qtype_name", "A"),
            )

            record = self._detector.analyse(record)
            if record.alert_flag:
                ALERTS_FIRED.inc()  # Count every laert
                logger.warning("[!!] %s → %s", record.reason, record.query_string)
                self._shipper.ship(record)
