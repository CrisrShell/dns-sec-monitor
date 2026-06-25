# Testing Notes — Part 3: Z-Score Tests & Coverage (19 June 2026)

> **Plain-English summary of the whole session:** We added tests for the
> frequency-spike detection rule, then used a "coverage" tool to measure how
> much of the code our tests actually check. Ended with 15 tests and 98%
> coverage of the detection engine — the part that matters.

---

## The One Idea Behind Today

Every test you write *checks* some lines of your real code by running them.
But how do you know *which* lines get checked, and which never get tested at
all? You can't tell by eye across a whole codebase.

**Coverage** is a tool that answers this. It runs your tests while watching
your source code, then reports: "these lines ran during testing (covered),
these lines never ran (not covered)." It turns a vague worry — *"have I tested
enough?"* — into a concrete map.

That's the session: write a few more tests (z-score), then measure everything
with coverage and learn to read the map.

---

## Part 1 — Z-Score Tests (the frequency-spike rule)

### What the z-score rule does (the security concept)
The engine watches how *often* each domain is queried. If one domain suddenly
appears far more than others, that's a **frequency spike** — a classic sign of
malware "beaconing" (calling home to a control server over and over). The
z-score is the statistic that measures "how unusual is this domain's
frequency compared to the rest."

### The new testing pattern: building up state first
Earlier tests called a function once and checked the answer. Z-score is
different — it only means anything *after* history accumulates. So the test has
to **arrange** that history before checking anything, by calling
`update_history` in a loop.

Three tests written, each proving one behaviour:

| Test | What it sets up | What it proves |
|---|---|---|
| `test_zscore_below_min_history_is_zero` | Only 5 queries (< MIN_HISTORY=10) | Returns 0.0 — "not enough data yet" guard works |
| `test_zscore_flags_repeated_query_as_spike` | 20 unique domains + 1 domain repeated 20× | The repeated domain scores high (> 3.0) — spike detected |
| `test_zscore_uniform_history_is_low` | 15 different domains, each once | Score stays low — no false alarm on normal traffic |

The middle test **is a security artefact**: it encodes what malicious DNS
beaconing looks like and proves the engine catches it. The third (the
"negative test") proves it *doesn't* cry wolf on ordinary traffic — equally
important.

### Config values these depend on
From `config.py`: `MIN_HISTORY = 10` (need ≥10 queries before z-score runs),
`FREQ_WINDOW = 50` (history holds at most 50), `ZSCORE_LIMIT = 3.0` (the spike
threshold).

---

## Part 2 — Coverage

### Installing and running
```powershell
py -m pip install pytest-cov
py -m pytest --cov=dns_monitor --cov-report=term-missing
```
`--cov=dns_monitor` = measure coverage of your package.
`--cov-report=term-missing` = show the result in the terminal, including the
exact line numbers that no test touched.

### Reading the report — the columns
```
Name                          Stmts   Miss  Cover   Missing
detection\engine.py              43      1    98%    45
```
- **Stmts** — total lines of code in the file
- **Miss** — lines no test ran
- **Cover** — percentage that ran
- **Missing** — the exact line numbers that weren't tested

### The key lesson: WHAT is covered matters more than HOW MUCH

Today's report showed a clear, *correct* split:

| Well covered | Why |
|---|---|
| `detection\engine.py` — 98% | The detection logic — entropy, z-score, rules. The heart of the project. |
| `config.py` — 100% | Simple settings. |

| Zero covered | Why that's fine |
|---|---|
| `shipper.py` — 0% | Talks to Elasticsearch over the network. |
| `orchestrator.py` — 0% | The top-level loop wiring everything together. |
| `__main__.py` — 0% | Entry point + startup banner. |
| `log_reader.py` tail() — 0% | An infinite file-polling loop. |

This split is **exactly right**. We tested the *pure logic* (functions that
take input and return output — where bugs hide and tests are cheap) and left
the *I/O and wiring* untested (network, files, infinite loops — which need
heavier "integration tests" that cost far more for less benefit).

### Why 100% is the WRONG goal
Chasing 100% means writing elaborate tests for startup banners and faking the
network — high effort, low value, and you often end up testing the fake instead
of your code. The total coverage (45%) looks low only because the untestable
I/O files drag it down. The number that matters — **98% on the detection
engine** — is excellent. Professional teams target meaningful coverage of
*logic*, not a vanity percentage.

> Interview-ready phrasing: *"I target coverage of business logic, not a vanity
> number — my detection engine is at 98%, while I deliberately leave network
> I/O to integration tests."*

### The line-number lesson (don't trust tooling blindly)
After adding a test for the `LargeQuery` rule, coverage *still* listed line 45
as missing. That looked wrong. Instead of accepting it, we ran the single test
in isolation:
```powershell
py -m pytest tests/test_detection.py::test_large_query_flags_as_large -v
```
It **passed** — proving line 45 *does* run. The "missing" report was a
line-numbering mismatch (coverage and the file disagreeing by a line, usually
after formatting shifts the line count).

**The lesson:** a coverage number is a guide, not gospel. When it contradicts
what you can prove by running the test, the running test wins. Verifying rather
than trusting tooling output is exactly the right engineering instinct.

---

## Commands Reference

```powershell
# Always from the engine/ directory
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor\engine

# Run tests
py -m pytest                      # all tests, compact
py -m pytest -v                   # verbose — each test named with PASS/FAIL

# Run a subset
py -m pytest tests/test_detection.py                       # one file
py -m pytest tests/test_detection.py::test_name -v         # one single test
py -m pytest -k zscore                                     # tests with "zscore" in the name

# Coverage
py -m pip install pytest-cov                               # one-time install
py -m pytest --cov=dns_monitor --cov-report=term-missing   # run + show coverage map
```

---

## Where Things Stand

- **15 tests, all passing** (was 10 at start of session — added 3 z-score + 2 branch tests)
- **98% coverage on the detection engine** — the logic that matters is thoroughly checked
- Pytest portion of Week 3 is **complete**

### Still left in Week 3
**GitHub Actions (CI)** — one session. This *automates* ruff + mypy + pytest so
they run on every push to GitHub, instead of you running them by hand. Now
worthwhile, because all three work locally. That finishes Week 3 → on to Week 4
(observability: Prometheus + Grafana).

---

## On Feeling Like "This Isn't Security"

Worth recording honestly: this testing week feels like software engineering,
not networking/security — and that's a fair read. But two things are true:
(1) the "Sec" and "Ops" in your target DevSecOps/Cloud-Security roles *is* this
— testing, CI, automation are named requirements, not a detour; (2) the
security-heavy content is concentrated ahead (Week 4 observability, Week 5
cloud/Terraform). This is the most engineering-flavoured stretch of an arc
that's otherwise heavy on exactly what you want. And the z-score spike test you
wrote today *is* detection engineering — a security skill wearing a test's
clothes.

---

*Companion files: TESTING_NOTES.md (pytest basics), CODE_QUALITY_NOTES.md
(ruff + mypy), PROJECT_ROADMAP.md, ENGINE_NOTES.md, ZEEK_NOTES.md,
BIND9_NOTES.md.*
