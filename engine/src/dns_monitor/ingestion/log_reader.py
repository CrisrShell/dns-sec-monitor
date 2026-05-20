# Tails the Zeek dns.log file and parses JSON lines

from __future__ import annotations

import json
import time
from typing import Generator, Optional


class LogReader:
    """Tails the Zeek dns.log file in real time. No analysis logic."""

    def __init__(self, path: str) -> None:
        self.path: str = path

    def tail(self) -> Generator[str, None, None]:
        """Yield new log lines as they appear. Polls every 100ms."""
        with open(self.path, "r") as f:
            f.seek(0, 2)  # Jump to end of file
            while True:
                line = f.readline()
                if line:
                    yield line
                else:
                    time.sleep(0.1)

    def parse_line(self, line: str) -> Optional[dict]:
        """Parse one JSON line. Returns None for malformed input (NFR4)."""
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None
