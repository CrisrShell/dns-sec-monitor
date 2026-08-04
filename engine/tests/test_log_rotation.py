"""Reproduces the log-rotation bug: reader must notice when the file
at its path is replaced/reset (as Zeek does hourly) and follow the new content."""

from __future__ import annotations

from dns_monitor.ingestion.log_reader import LogReader


def test_reader_follows_rotated_file(tmp_path):
    log = tmp_path / "dns.log"
    log.write_text("old line\n")

    reader = LogReader(str(log))
    gen = reader.tail()  # open + seek-to-end happen HERE now (eager)

    # Sanity: a line appended after attach is seen
    with open(log, "a") as f:
        f.write("line before rotation\n")
    assert next(gen).strip() == "line before rotation"

    # Simulate rotation: replace content at the same path (file shrinks).
    # (os.remove on an open file fails on Windows; content-replacement is
    # the portable simulation, and shrinkage is a real rotation signal.)
    log.write_text("line after rotation\n")

    # The reader should notice and deliver the new file's first line
    assert next(gen).strip() == "line after rotation"
