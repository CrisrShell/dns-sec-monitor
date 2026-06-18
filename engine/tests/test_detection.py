"""Tests for the DetectionEngine — starting with Shannon entropy."""

from __future__ import annotations

import math

from dns_monitor.detection.engine import DetectionEngine

from dns_monitor.core.record import DNSRecord 


def test_entropy_of_empty_string_is_zero():
    # Arrange — make an engine to test
    engine = DetectionEngine()
    # Act — call the function
    result = engine.calculate_entropy("")
    # Assert — state what must be true
    assert result == 0.0


def test_entropy_of_single_repeated_char_is_zero():
    # "aaaa" has one symbol → no uncertainty → entropy 0
    engine = DetectionEngine()
    assert engine.calculate_entropy("aaaa") == 0.0


def test_entropy_of_two_equal_chars_is_one_bit():
    # "abab" — two symbols, equally likely → exactly 1.0 bit
    engine = DetectionEngine()
    assert engine.calculate_entropy("abab") == 1.0


def test_tunnelling_string_has_high_entropy():
    # A long random subdomain like real DNS tunnelling — entropy should be high
    engine = DetectionEngine()
    suspicious = "j5h9g3f7d1s8a2k6l0z4x8c2v6b0n4m8"
    # We don't care about the exact number, only that it crosses the alert line
    assert engine.calculate_entropy(suspicious) > 4.0

def _make_record(query: str, rcode: str = "NOERROR") -> DNSRecord:
    """Helper — build a DNSRecord with the fields analyse() needs."""
    return DNSRecord(
        timestamp="2026-06-18T00:00:00Z",
        source_ip="172.18.0.1",
        query_string=query,
        rcode=rcode,
    )


def test_normal_query_does_not_alert():
    # A short, ordinary domain should trip no rules
    engine = DetectionEngine()
    record = engine.analyse(_make_record("google.com"))
    assert record.alert_flag is False
    assert record.reason == ""


def test_nxdomain_sets_alert_flag():
    # An NXDOMAIN response should flag, with NXDOMAIN in the reason
    engine = DetectionEngine()
    record = engine.analyse(_make_record("nope.example.com", rcode="NXDOMAIN"))
    assert record.alert_flag is True
    assert "NXDOMAIN" in record.reason


def test_high_entropy_query_flags_and_scores():
    # A long random subdomain — the tunnelling signature
    engine = DetectionEngine()
    suspicious = "j5h9g3f7d1s8a2k6l0z4x8c2v6b0n4m8.google.com"
    record = engine.analyse(_make_record(suspicious))
    assert record.alert_flag is True
    assert "HighEntropy" in record.reason
    assert record.entropy_score > 4.0