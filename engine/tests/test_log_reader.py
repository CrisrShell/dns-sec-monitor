"""Tests for LogReader — focuses on parse_line (good input vs malformed)."""

from __future__ import annotations

from dns_monitor.ingestion.log_reader import LogReader


def test_parse_valid_json_returns_dict():
    # Arrange — a realistic Zeek dns.log line
    reader = LogReader(path="unused")  # path not needed for parse_line
    line = '{"query": "google.com", "rcode_name": "NOERROR"}'
    # Act
    result = reader.parse_line(line)
    # Assert — we get a dict back with the right contents
    assert result is not None
    assert result["query"] == "google.com"


def test_parse_malformed_json_returns_none():
    # NFR4: bad input must not crash — it returns None
    reader = LogReader(path="unused")
    result = reader.parse_line("this is not json {{{")
    assert result is None


def test_parse_empty_line_returns_none():
    # An empty line is also malformed JSON → None, no crash
    reader = LogReader(path="unused")
    assert reader.parse_line("") is None
