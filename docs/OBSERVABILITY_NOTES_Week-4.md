# Observability Notes — Part 1: Metrics & Prometheus (Week 4)

> **Plain-English summary:** The engine now counts what it does (queries
> processed, alerts fired) and publishes those numbers on a small web page.
> A new Prometheus container fetches that page every 15 seconds and stores the
> values over time. Proven end-to-end: counters visible and climbing in
> Prometheus's own query UI.
>
> **Remaining for Week 4:** Grafana — the dashboard layer over Prometheus.

---

## Why Observability (the motivating memory)

In Week 2 the engine sat silently reading a dead file for an hour and nothing
looked wrong — silence was indistinguishable from health. Observability fixes
exactly that: making a system's **internal state visible from outside**.
Detection tells you about the *traffic*; observability tells you about the
*monitor itself*.

---

## Key Concepts

### Metric
A named number that changes over time. Three types:

| Type | Behaviour | Example |
|---|---|---|
| **Counter** | Only goes up (resets to 0 on restart) | total queries processed |
| **Gauge** | Goes up and down | memory in use, queue size |
| **Histogram** | Distribution of values | processing latency spread |

We used two Counters: `dns_queries_processed_total`, `dns_alerts_fired_total`.
(Convention: counters end in `_total`.)

### Scraping (Prometheus's pull model)
The engine does **not** send metrics anywhere. It just serves a text page at
`/metrics` with current values. Prometheus repeatedly **pulls** ("scrapes")
that page — every 15s in our config — and stores each reading with a
timestamp. App stays simple; the collector does the work.

### The /metrics page format
Plain text, three line types:
```
# HELP dns_queries_processed_total Total DNS queries processed
# TYPE dns_queries_processed_total counter
dns_queries_processed_total 4.0
```
`prometheus-client` also adds free metrics you didn't write (`python_gc_*`,
`python_info` — process health) and a `_created` companion per counter (birth
timestamp; used to detect restarts; ignorable).

### Container-to-container networking (the localhost trap)
Inside a container, `localhost` means *that container itself*. Prometheus
cannot reach the engine at `localhost:9100` — it reaches it by **service
name**: `engine:9100`. Docker's built-in DNS resolves service names on the
shared network. (Same pattern as Kibana → `elasticsearch:9200`.)

### Named services vs the whole stack
`docker compose up -d engine` starts *only* engine + its declared
dependencies. Kibana didn't start simply because nothing we named depends on
it — no edit disabled it. Plain `docker compose up -d` starts everything.
Also: Prometheus does not replace Kibana — Kibana visualises **alerts**
(Elasticsearch data), Prometheus/Grafana visualise **engine health**.
Different data, both stay.

---

## What Was Built

### 1. Instrumented the engine (`orchestrator.py`)
Four small edits:

```python
from prometheus_client import Counter, start_http_server

# Module-level — must persist for the process's whole life
QUERIES_PROCESSED = Counter(
    "dns_queries_processed_total",
    "Total DNS queries the engine has processed",
)
ALERTS_FIRED = Counter(
    "dns_alerts_fired_total",
    "Total alerts the engine has raised",
)

def run(self) -> None:
    start_http_server(9100)          # /metrics server, own thread, non-blocking
    for raw_line in self._reader.tail():
        ...
        QUERIES_PROCESSED.inc()      # +1 per valid query
        ...
        if record.alert_flag:
            ALERTS_FIRED.inc()       # +1 per alert
```

Tested in isolation first with a throwaway script + browser at
`http://localhost:9100/metrics` — proved the mechanism before touching
containers.

### 2. Dockerfile fixes (one real bug caught)
The builder stage **hardcodes** dependencies:
```dockerfile
RUN pip install --no-cache-dir --prefix=/install pandas elasticsearch prometheus-client
```
`prometheus-client` had to be added by hand — the Dockerfile ignores
`pyproject.toml`, so the two lists can drift. Without this, the rebuilt engine
would crash on import. **Backlog:** install from `pyproject.toml` so the list
can't drift again.

Also added, before `USER dnsmonitor`:
```dockerfile
EXPOSE 9100
```

### 3. Prometheus config (`infra\prometheus\prometheus.yml`)
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "dns-engine"
    static_configs:
      - targets: ["engine:9100"]     # service name, not localhost
```
Reading: "every 15s, fetch http://engine:9100/metrics and store it."

### 4. Prometheus container (`docker-compose.yml`)
```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: dns-prometheus
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"                  # Prometheus web UI
    networks:
      - dns-net
    depends_on:
      - engine
    restart: unless-stopped
```
Plus `prometheus-data:` added to the volumes list.

---

## Verification (the proof chain)

1. `http://localhost:9090/targets` → target `dns-engine` at
   `http://engine:9100/metrics`, state **UP** = scraping works.
2. `http://localhost:9090/graph` → query `dns_queries_processed_total` →
   value returned **from Prometheus's database**, not the engine directly.
3. Fired a high-entropy test query → both counters moved to 4
   (A + AAAA × both captured legs — the Week 2 duplication, still on backlog).

**Reading the numbers:** queries=4 AND alerts=4 means every query since
restart was the test itself. In normal traffic queries outpaces alerts — that
*gap* (alert rate vs traffic rate) is exactly what a Grafana dashboard makes
visible at a glance.

Counter showed 0 before the test — correct, not a fault: the engine restarted
after earlier traffic and `tail()` seeks to end-of-file (Week 2 Bug 6), so
pre-restart events are invisible to it.

---

## Old Friends That Reappeared

- **Startup race (Week 2 Bug 6):** fresh Zeek deploy → no `dns.log` → engine
  `FileNotFoundError` restart-loop → self-heals after one DNS query creates
  the file. Recognised in seconds this time.
- A traceback reaching `run()` proved the `prometheus_client` import worked —
  reading *where* a crash happens tells you what already succeeded.

---

## Commands Reference

```powershell
# Local dev (from engine/)
py -m pip install prometheus-client
py -m ruff check --fix .            # new import needs sorting into place
py -m ruff format .

# Rebuild engine (picks up new dependency + EXPOSE), start Prometheus
docker compose up -d --build engine
docker compose up -d prometheus
docker compose ps

# If engine restart-loops with FileNotFoundError — feed it a packet:
Resolve-DnsName google.com -Server 127.0.0.1

# Verify
# Browser: http://localhost:9090/targets   (target UP?)
# Browser: http://localhost:9090/graph     (query the counter names)

# Generate a test alert (fresh random name each time)
Resolve-DnsName "<24+ random chars>.google.com" -Server 127.0.0.1
```

---

## Week 4 Remaining

| Item | What it involves |
|---|---|
| **Grafana container** | Add to compose, connect Prometheus as data source, build a dashboard: query rate + alert rate over time. The visually satisfying half. |
| Optional extras | A Gauge or Histogram (e.g. processing latency) once the dashboard exists; alert-rate panel makes the Week 2 dedup issue visible. |

---

*Companion files: CI_NOTES.md, TESTING_NOTES*.md, CODE_QUALITY_NOTES.md,
ENGINE_NOTES.md, ZEEK_NOTES.md, BIND9_NOTES.md.*
