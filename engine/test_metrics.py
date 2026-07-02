"""Throwaway — verify the metrics server works in isolation."""
import time

from prometheus_client import Counter, start_http_server

TEST_COUNTER = Counter("dns_queries_processed_total", "test")

start_http_server(9100)
print("Metrics live at http://localhost:9100/metrics")
print("Incrementing every 2s. Ctrl+C to stop.")
while True:
    TEST_COUNTER.inc()
    time.sleep(2)