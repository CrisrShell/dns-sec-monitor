# Testing Notes — Session of 18 June 2026 (Week 3, Part 2)

> **Focus:** pytest — first exposure. Wrote 10 tests across the engine's core
> logic. All passing.
> **Deferred:** z-score tests, coverage report, GitHub Actions CI.

---

## What a Test Actually Is

A test is a small function that does three things — the **AAA pattern**:

1. **Arrange** — set up a known input
2. **Act** — call the function being tested
3. **Assert** — state what the result *should* be; if reality differs, fail

The key word is **`assert`** — a Python statement meaning "this must be true."
`assert 2 + 2 == 4` passes silently; `assert 2 + 2 == 5` raises an error. A
test is a function full of asserts about your code's behaviour.

## Why Test Code Lives in Separate Files

Test code and real code are deliberately separate:

| File | Job |
|---|---|
| `src/.../engine.py` | The **real code**. Ships, runs in production. No tests inside. |
| `tests/test_detection.py` | The **test code**. No business logic. Imports real code, feeds it inputs, checks outputs. |

The bridge is the **import line** at the top of each test file:
```python
from dns_monitor.detection.engine import DetectionEngine
```
That reaches into the real code and pulls the class into the test. The test
then calls the *real* function with known inputs. So the logic stays in
`engine.py`; the test is a thin harness *around* it. Change the real code,
re-run the tests, instantly know if you broke something.

## How pytest Finds Tests (convention, no registration)

- Test files named `test_*.py`
- Test functions named `test_*`

pytest scans, finds matches, runs them. A helper function *not* named `test_`
(like `_make_record`) is ignored by the runner — useful for shared setup.

---

## The Three Patterns Learned

### 1. Return-value (the entropy tests)
Give input, check the number that comes back. Best first target because the
answers are knowable from maths:
- empty string → 0.0
- `"aaaa"` (one symbol) → 0.0
- `"abab"` (two equal symbols) → exactly 1.0 bit
- long random string → entropy > 4.0 (threshold assert, not exact value)

Two assert styles: **exact** (`== 1.0`) for clean cases, **threshold**
(`> 4.0`) when you only care that it crosses a line.

### 2. Happy-path + failure-path (the parser tests)
One function, two behaviours to verify:
- valid JSON in → dict out
- malformed JSON in → `None` out (proves the NFR4 "don't crash on bad data"
  guarantee actually holds)
- empty string in → `None` out

The failure-path test is the valuable one — it proves resilience, exactly what
an interviewer probes.

### 3. Behaviour-and-state (the analyse() tests)
Feed a record, assert which rules fired and why:
- normal query → `alert_flag is False`, `reason == ""` (the **negative test** —
  proves no false alarms on ordinary traffic; the one people forget)
- NXDOMAIN → `alert_flag is True` AND `"NXDOMAIN" in reason`
- high-entropy → flagged AND `entropy_score > 4.0`

Pattern: one assert proves it *fired*, another proves it fired for the *right
reason*.

### Helper functions reduce repetition
`_make_record(...)` builds a valid `DNSRecord` so each test doesn't repeat the
six-field constructor. Not named `test_`, so pytest skips it. Tidy tests matter
as much as tidy code.

---

## Test one thing, in isolation
`parse_line` doesn't touch the file, so tests pass a dummy `path="unused"` —
testing *only* the parsing, separated from file-tailing. Isolating each unit is
the core discipline of unit testing.

---

## The `src` Layout Problem (and fix)

Tests failed first run with `ModuleNotFoundError: No module named 'dns_monitor'`.
Cause: code lives in `engine/src/`, but `src/` isn't on Python's import search
path by default (the `src` layout — deliberate, professional structure). The
container handles this via `PYTHONPATH=/app/src`; Windows pytest doesn't know
that.

**Fix — install your own package in editable mode:**
```powershell
py -m pip install -e .
```
`-e` = editable (points at live source, edits take effect immediately),
`.` = the package defined by this directory's `pyproject.toml`. Standard way to
make a `src`-layout project testable. One-time setup.

**Second latent bug found en route:** the editable install failed because
`pyproject.toml` had `readme = "../README.md"` — pip refuses to read files
outside the package directory (a security boundary). Removed the line (it's
publishing metadata, irrelevant to a non-published portfolio project). The root
README itself is untouched — still the repo's GitHub front page.

Pattern repeating all week: tools surface bugs that were always latent, only
exposed when a new code path runs them.

---

## Commands Reference

```powershell
# Run from the engine/ directory (where pyproject.toml + tests/ live)
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor\engine

py -m pip install -e .       # ONE-TIME: make dns_monitor importable for tests
py -m pytest                 # run all tests (dots: . = pass, F = fail)
py -m pytest -v              # verbose — lists each test by name with PASS/FAIL
py -m pytest tests/test_detection.py   # run one file only
py -m pytest -k entropy      # run only tests whose name contains "entropy"
```

**Where to run:** package/test commands → from `engine/`. Git commands → from
the repo root. Tell which directory you're in from the prompt tail:
`...\engine>` = ready for pytest; `...\dns-sec-monitor>` = `cd engine` first.

---

## Current Test Suite (10 tests, all passing)

```
tests/test_detection.py   (7)
  entropy: empty, single-char, two-char, tunnelling-string
  analyse: normal (no alert), NXDOMAIN, high-entropy
tests/test_log_reader.py  (3)
  parse: valid JSON, malformed JSON, empty line
```

Covers the project's core logic: the entropy calculation (headline feature),
the rule orchestration, and the input parser's resilience.

---

## Still To Do (next sessions)

| Item | Notes |
|---|---|
| **z-score tests** | `calculate_zscore` + `update_history` — needs building up a window of history first; slightly more involved setup. |
| **Coverage report** | `pytest-cov` shows which lines are/aren't tested — reveals gaps honestly. |
| **GitHub Actions CI** | Automate ruff + mypy + pytest on every push. Now worthwhile — all three work locally by hand. |
| Tests for the Week 2 bugs | Rotation-aware LogReader + retry-on-missing-file: write a failing test that reproduces each bug, then fix the code. |

---

## Notes on environment

- pytest installed under Python 3.13 (`Python313`), while the project targets
  3.12. Fine for pure-logic tests; keep in mind if anything odd appears.
- The PATH warnings during pip install are harmless — they refer to `.exe`
  shortcuts we don't use (`py -m pytest` always works regardless of PATH).

---

*Companion files: CODE_QUALITY_NOTES.md (ruff + mypy), ENGINE_NOTES.md,
ZEEK_NOTES.md, BIND9_NOTES.md.*
