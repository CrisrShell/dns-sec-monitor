"""Tests for the DetectionEngine — starting with Shannon entropy."""

from __future__ import annotations

from dns_monitor.core.record import DNSRecord
from dns_monitor.detection.engine import DetectionEngine


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


def test_zscore_below_min_history_is_zero():
    # MIN_HISTORY is 10 — with fewer entries, z-score returns 0.0 (the guard)
    engine = DetectionEngine()
    for _ in range(5):  # only 5 < 10
        engine.update_history("google.com")
    assert engine.calculate_zscore("google.com") == 0.0


def test_zscore_flags_repeated_query_as_spike():
    # Build a window where one domain dominates a field of varied others.
    # That domain's frequency should sit far above the mean → high z-score.
    engine = DetectionEngine()
    for i in range(20):
        engine.update_history(f"unique-domain-{i}.com")  # 20 distinct, count 1 each
    for _ in range(20):
        engine.update_history("flood.example.com")  # 1 domain, count 20
    z = engine.calculate_zscore("flood.example.com")
    assert z > 3.0  # ZSCORE_LIMIT — this query would trip the FreqSpike rule


def test_zscore_uniform_history_is_low():
    # If every domain appears equally often, none is a spike → z near zero.
    engine = DetectionEngine()
    for i in range(15):
        engine.update_history(f"domain-{i}.com")  # all distinct, all count 1
    z = engine.calculate_zscore("domain-0.com")
    assert z < 3.0


def test_large_query_flags_as_large():
    # A query over LENGTH_LIMIT (50) trips LargeQuery.
    # All-"a" → entropy 0, so ONLY the length rule fires (isolates the branch).
    engine = DetectionEngine()
    record = engine.analyse(_make_record("a" * 60))
    assert record.alert_flag is True
    assert "LargeQuery" in record.reason


def test_freq_spike_flags_repeated_query():
    # Build a window where one domain dominates, then analyse it —
    # the z-score should cross ZSCORE_LIMIT (3.0) and trip FreqSpike.
    engine = DetectionEngine()
    for i in range(20):
        engine.update_history(f"unique-{i}.com")
    for _ in range(20):
        engine.update_history("flood.example.com")
    record = engine.analyse(_make_record("flood.example.com"))
    assert "FreqSpike" in record.reason
