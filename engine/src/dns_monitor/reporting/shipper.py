"""Persists alerts to CSV, HTML, and Elasticsearch independently."""

from __future__ import annotations

import logging
import os

import pandas as pd
import urllib3
from elasticsearch import Elasticsearch

from dns_monitor.config import CSV_OUT, ES_HOST, ES_INDEX, ES_PASS, ES_USER, HTML_OUT
from dns_monitor.core.record import DNSRecord

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("dns_monitor")


class AlertShipper:
    """Persists alerts to CSV, HTML, and Elasticsearch independently."""

    def __init__(self) -> None:
        self._init_files()
        self._es: Elasticsearch = Elasticsearch(
            ES_HOST, basic_auth=(ES_USER, ES_PASS), verify_certs=False
        )

    def _init_files(self) -> None:
        """Create CSV header and HTML placeholder if they do not exist."""
        if not os.path.exists(CSV_OUT):
            pd.DataFrame(
                columns=["timestamp", "src", "query", "type", "entropy_score", "reason"]
            ).to_csv(CSV_OUT, index=False)
        with open(HTML_OUT, "w") as f:
            f.write(
                "<html><head><meta http-equiv='refresh' content='5'></head>"
                "<body><h1>DNS Security Dashboard</h1><p>Monitoring...</p></body></html>"
            )

    def ship(self, record: DNSRecord) -> None:
        """Send an alert to all three output targets."""
        self._write_csv(record)
        self._update_html()
        self._send_to_elasticsearch(record)

    def _write_csv(self, record: DNSRecord) -> None:
        """Append a single alert row with full quoting to prevent corruption."""
        pd.DataFrame([record.to_dict()]).to_csv(
            CSV_OUT, mode="a", index=False, header=False, quoting=1
        )

    def _update_html(self) -> None:
        """Rebuild the HTML dashboard from the last 15 CSV entries."""
        try:
            df = pd.read_csv(CSV_OUT, quoting=1).tail(15)
            df.to_html(HTML_OUT, index=False, classes="table table-dark table-striped")
        except Exception as e:
            logger.warning("HTML dashboard update failed: %s", e)

    def _send_to_elasticsearch(self, record: DNSRecord) -> None:
        """Index alert document into Elasticsearch."""
        try:
            res = self._es.index(index=ES_INDEX, document=record.to_dict())
            logger.info("ELK indexed: %s", res["result"])
        except Exception as e:
            logger.error("ELK indexing failed: %s", e)

