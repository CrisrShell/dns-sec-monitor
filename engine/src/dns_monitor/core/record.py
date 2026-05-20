
""" DNS event data model """

from __future__ import annotation

from dataclasses import dataclass
from typing import Optional


@dataclass
class DNSRecord:
    """A single parsed DNS event with detection metadata."""

    timestamp: str
    source_ip: Optional[str]
    query_string: str
    rcode: str
    query_type: str = "A"
    entropy_score: float = 0.0
    alert_flag: bool = False
    reason: str = ""

    def to_dict(self) -> dict:
        """Serialise to JSON-compatible dict for storage and indexing."""
        return {
            "timestamp": self.timestamp,
            "src": self.source_ip,
            "query": self.query_string,
            "type": "ALERT" if self.alert_flag else "NORMAL",
            "entropy_score": self.entropy_score,
            "alert_flag": self.alert_flag,
            "reason": self.reason,
            "alert_category": self._categorise(),
        }

    def _categorise(self) -> str:
        """Return clean normalised category label for dashboard display."""
        if not self.reason:
            return "Normal"
        labels: list[str] = []
        if "HighEntropy" in self.reason:
            labels.append("High Entropy")
        if "LargeQuery" in self.reason:
            labels.append("Large Query")
        if "NXDOMAIN" in self.reason:
            labels.append("NXDOMAIN")
        if "FreqSpike" in self.reason:
            labels.append("Frequency Spike")
        return " + ".join(labels) if labels else "Other"