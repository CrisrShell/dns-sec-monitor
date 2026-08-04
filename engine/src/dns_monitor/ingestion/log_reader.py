# Tails the Zeek dns.log file and parses JSON lines

from __future__ import annotations

import json
import os
import time
from collections.abc import Generator
from typing import TextIO


class LogReader:
    """Tails the Zeek dns.log file in real time. No analysis logic."""

    def __init__(self, path: str) -> None:
        self.path: str = path

    def tail(self) -> Generator[str, None, None]:
        """Open the log and follow it, surviving log rotation.
        Open+seek happen immediately; only the line-yielding loop is lazy."""
        # noqa justification: handle must outlive this method — the generator
        # owns it and manages close/reopen during rotation (see _follow).
        f = open(self.path)  # noqa: SIM115
        f.seek(0, 2)  # Jump to end of file
        return self._follow(f)

    def parse_line(self, line: str) -> dict | None:
        """Parse one JSON line. Returns None for malformed input (NFR4)."""
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def _rotated(self, f: TextIO) -> bool:
        """Has the file at self.path been replaced or reset (log rotation)?

        Two signals, either one means rotation:
        - inode changed: a NEW file now sits at the path (Linux rotation)
        - file shrank: the file at the path is smaller than our read
          position (rotation reset it — also how we simulate on Windows)
        """
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return False  # path briefly absent mid-rotation — wait, don't reopen yet
        return st.st_ino != os.fstat(f.fileno()).st_ino or st.st_size < f.tell()

    def _follow(self, f: TextIO) -> Generator[str, None, None]:
        while True:
            line = f.readline()
            if line:
                yield line
            else:
                # No new line — before sleeping, check for rotation
                if self._rotated(f):
                    f.close()
                    f = open(self.path)  # noqa: SIM115  (rotation reopen — lifetime managed here)
                    continue  # read from the start (top = new data)
                time.sleep(0.1)
