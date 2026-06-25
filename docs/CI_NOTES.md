# CI / GitHub Actions Notes — Week 3 Completion (25 June 2026)

> **Plain-English summary:** GitHub Actions automatically runs all your quality
> checks (ruff, mypy, pytest) on a fresh cloud computer every time you push to
> GitHub. You stopped relying on remembering to run them — GitHub runs them for
> you, every push, and shows a green "passing" badge when they succeed.
>
> **This completes Week 3.**

---

## What CI Is (the concept)

**CI = Continuous Integration.** Every push to GitHub triggers a fresh Ubuntu
machine in the cloud to run your checks and report pass/fail.

| Without CI | With CI |
|---|---|
| You must remember to run ruff/mypy/pytest by hand | GitHub runs them automatically on every push |
| A broken commit can slip in unnoticed | A broken commit fails visibly, immediately |
| No outward signal of quality | A green "passing" badge on the README |

**Why it matters for your target roles:** the "Ops" in DevSecOps is largely
this — automated pipelines that enforce quality without human memory. A passing
CI badge is a signal recruiters and engineers recognise instantly.

---

## How It Works (mechanics)

1. You write a **workflow file** (YAML) describing the steps.
2. GitHub watches a special folder: `.github/workflows/` (at the repo **root**,
   not inside `engine/`).
3. On every push, GitHub spins up a fresh cloud machine and runs your steps.
4. Each step goes green (pass) or red (fail). One red step fails the whole run.

Analogy: you write the recipe; GitHub provides the kitchen and cooks it every
time you push.

---

## The Workflow File

Location: `.github/workflows/ci.yml`

```yaml
name: CI                          # Name shown in the Actions tab

on:                               # WHEN to run
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest        # The fresh cloud machine
    defaults:
      run:
        working-directory: engine # All commands run from engine/
    steps:
      - name: Check out code               # 1. Copy repo onto the machine
        uses: actions/checkout@v4
      - name: Set up Python                # 2. Install Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies         # 3. Install package + dev tools
        run: pip install -e ".[dev]"
      - name: Ruff lint                     # 4. Lint
        run: ruff check .
      - name: Ruff format check             # 5. Format check (no edits)
        run: ruff format --check .
      - name: Mypy                          # 6. Type check
        run: mypy src
      - name: Pytest                        # 7. Tests + coverage
        run: pytest --cov=dns_monitor
```

### Key details worth understanding

- **`pip install -e ".[dev]"`** — installs your package *plus* the `dev`
  dependency group (ruff, mypy, pytest, pytest-cov) in one command. Works
  because they're all declared in `pyproject.toml`.
- **Python 3.12 in CI, 3.13 locally** — CI runs your *actual target* version.
  If anything differs between versions, CI catches it. This is a feature.
- **`ruff format --check`** — the `--check` means "fail if formatting is wrong,
  but don't edit." In CI you want tools to *report*, never modify. If this step
  fails, run `ruff format .` locally and push again.
- **Bare commands (`ruff check .`) in the YAML** — correct for Ubuntu, where
  the install puts tools on PATH. Locally on Windows you still need `py -m ruff`
  because the PATH shortcuts aren't set up. Different environments, both fine.

---

## What CI Caught On First Setup

A real example of CI's value *before it even ran*: running the exact CI checks
locally revealed that the **test files** had lint + format issues — an unused
`import math` and unsorted imports in `test_detection.py`. Earlier sessions
only ran ruff on `src/`, never `tests/`. CI would have caught these on first
push; checking locally first caught them faster. Fixed with:

```powershell
py -m ruff check --fix .
py -m ruff format .
```

**Lesson:** CI enforces quality on *all* code, including tests — not just the
parts you remember to check.

---

## The Status Badge

The visible payoff. A live image at the top of the README showing green
"passing" or red "failing", read from the latest CI run.

Markdown (goes in `README.md`, not the terminal):
```markdown
![CI](https://github.com/USERNAME/REPO/actions/workflows/ci.yml/badge.svg)
```

**Get the exact URL from GitHub, don't hand-build it:** Actions tab → click the
workflow → `...` (three dots) → **Create status badge** → copy the generated
Markdown. This avoids username/repo typos (which show as a broken-image icon —
the failure mode hit during setup was a single missing letter in the username).

---

## The Node.js Deprecation Warning (harmless)

After a successful run, GitHub showed: *"Node.js 20 is deprecated... actions/
checkout@v4, actions/setup-python@v5..."*. This is **not your problem to fix**.
It's a notice about GitHub's own internal tooling inside the actions you used.
Your pipeline works. When newer action versions release (`checkout@v5` etc.),
bump the numbers — no urgency, nothing broken.

---

## Commands Reference

```powershell
# Run the EXACT checks CI will run, locally first (from engine/)
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor\engine
py -m ruff check .
py -m ruff format --check .
py -m mypy src
py -m pytest --cov=dns_monitor

# Auto-fix lint + format issues
py -m ruff check --fix .
py -m ruff format .

# Commit the workflow (from repo root — note the hidden .github folder)
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor
git add .github/ engine/
git commit -m "Add GitHub Actions CI"
git push origin main
# Then watch it run: repo → Actions tab
```

**Habit:** run the CI checks locally before pushing. Catching a failure on your
machine takes seconds; waiting for CI to fail takes a minute and clutters the
run history.

---

## Week 3 — Complete ✅

The full code-quality scaffold, built from zero prior experience with any of
these tools:

| Part | Tool | Result |
|---|---|---|
| 3a | ruff (lint + format) | Found a real bug, formatted all files, stricter rules |
| 3b | mypy (types) | Clean pass, library boundaries configured |
| 3c–3d | pytest (+ coverage) | 15 tests, 98% on detection engine |
| 3e | GitHub Actions (CI) | All three automated on every push, green badge |

**Three weeks done, three to go.**

### Next: Week 4 — Observability (Prometheus + Grafana)
Swings back to infrastructure/monitoring. Makes the engine's *health* visible —
queries processed, alerts fired, latency. Connects directly to the Week 2
"heartbeat logging" backlog item (silence looked like health; Prometheus is how
you fix that visibly).

---

*Companion files: TESTING_NOTES.md, TESTING_NOTES_PART3.md, CODE_QUALITY_NOTES.md,
PROJECT_ROADMAP.md, ENGINE_NOTES.md, ZEEK_NOTES.md, BIND9_NOTES.md.*
