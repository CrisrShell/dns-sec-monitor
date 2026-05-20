# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
def _startup_banner() -> None:
    """Print a one-time startup banner. Uses print() for visual emphasis."""
    print("=" * 70)
    print("  DNS Security Monitor v3")
    print("=" * 70)
    print(f"  Zeek log    : {ZEEK_LOG}")
    print(f"  CSV output  : {CSV_OUT}")
    print(f"  Elasticsearch: {ES_HOST}/{ES_INDEX}")
    print(f"  Thresholds  : H > {ENTROPY_LIMIT} | Len > {LENGTH_LIMIT} | Z > {ZSCORE_LIMIT}")
    print("=" * 70)


if __name__ == "__main__":
    _startup_banner()
    engine = DNSEngine()
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.info("Engine stopped by user.")