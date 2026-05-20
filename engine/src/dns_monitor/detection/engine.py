""" Statistical anomaly detection engine - applies 4 detection rules """

from __future__ import annotations

import math
from collections import Counter

from dns_monitor.config import (
    ENTROPY_LIMIT,
    FREQ_WINDOW,
    LENGTH_LIMIT,
    MIN_HISTORY,
    ZSCORE_LIMIT,
)
from dns_monitor.core.record import DNSRecord


class DetectionEngine:
    """Applies four statistical anomaly detection rules to every DNS event."""

    def __init__(self) -> None:
        self._history: list[str] = []

    def calculate_entropy(self, text: str) -> float:
        """Shannon Entropy H(X) = -Σ p(x) * log2(p(x))."""
        if not text:
            return 0.0
        probs = [text.count(c) / len(text) for c in set(text)]
        return round(-sum(p * math.log2(p) for p in probs), 4)

    def calculate_zscore(self, query: str) -> float:
        """Z-score of query frequency in the rolling window."""
        if len(self._history) < MIN_HISTORY:
            return 0.0
        counts = Counter(self._history)
        freqs = list(counts.values())
        mean = sum(freqs) / len(freqs)
        std = math.sqrt(sum((f - mean) ** 2 for f in freqs) / len(freqs))
        return (counts[query] - mean) / std if std > 0 else 0.0

    def update_history(self, query: str) -> None:
        """Slide the rolling window — append new, drop oldest if full."""
        self._history.append(query)
        if len(self._history) > FREQ_WINDOW:
            self._history.pop(0)

    def analyse(self, record: DNSRecord) -> DNSRecord:
        """Evaluate all four rules. Returns the same record with flags set."""
        self.update_history(record.query_string)
        reasons: list[str] = []

        # Rule 1 — NXDOMAIN response
        if record.rcode in ("NXDOMAIN", "3"):
            reasons.append("NXDOMAIN")

        # Rule 2 — Payload length anomaly
        if len(record.query_string) > LENGTH_LIMIT:
            reasons.append(f"LargeQuery({len(record.query_string)})")

        # Rule 3 — Shannon Entropy
        h = self.calculate_entropy(record.query_string)
        record.entropy_score = h
        if h > ENTROPY_LIMIT:
            reasons.append(f"HighEntropy(H={h})")

        # Rule 4 — Z-score frequency spike
        z = self.calculate_zscore(record.query_string)
        if z > ZSCORE_LIMIT:
            reasons.append(f"FreqSpike(Z={round(z, 2)})")

        if reasons:
            record.alert_flag = True
            record.reason = " | ".join(reasons)

        return record

