# Code Quality Notes — Session of 17 June 2026 (Week 3, Part 1)

> **Focus:** ruff (linter + formatter) and mypy (type checker) — first exposure.
> **Outcome:** Both tools installed, run, understood, and passing on the whole
> codebase with a stricter-than-default rule set. One real latent bug found and
> fixed. pytest and GitHub Actions deferred to their own sessions.

---

## The Mental Model — Three Different Jobs

These tools are easy to confuse because they all "check code." They do
different things:

| Tool | Job | Question it answers | Changes meaning? |
|---|---|---|---|
| **ruff check** (linter) | Find problems | "Is anything *wrong*?" | Can (you fix it) |
| **ruff format** (formatter) | Standardise layout | "Is it laid out *consistently*?" | **Never** — layout only |
| **mypy** (type checker) | Verify type hints | "Do the types line up?" | Can (you fix it) |

None of them *run* your code. They all reason about it statically (by reading
it). That's why they're fast and safe to run constantly.

---

## Ruff — Linter

A linter reads code without running it and flags issues: unused imports,
undefined names, lines too long, bug-prone patterns.

### The real bug it caught (the headline of the session)

In `__main__.py`:
- `import logging` — imported but never used (`F401`)
- `logger.info("Engine stopped by user.")` — `logger` was never defined (`F821`)

These were two halves of an **unfinished logging setup**. The line that
*creates* the logger (`logger = logging.getLogger(__name__)`) was never
written. The code looked fine but would have **crashed with `NameError` on
Ctrl+C** — the one moment that line runs.

**Fix chosen:** match the file's existing style (it uses `print` everywhere) —
removed the import, changed the call to `print(...)`. Converting the whole
project to proper logging is a real improvement but a *feature change*, not a
lint fix — backlogged separately.

**Lesson:** this is exactly what a linter is for — an invisible bug, harmless
until one specific moment, found in under a second without running anything.

### Ruff — Formatter

Separate from the linter. Rewrites *layout only* — spacing, blank lines, quote
style, line wrapping — to one consistent standard. Never changes behaviour.

On this codebase it: removed stray blank first lines, added end-of-file
newlines (POSIX convention), tidied docstring spacing, wrapped one over-long
line. 5 of 13 files had minor drift; formatting made all 13 consistent.

### Tightening the rules

Ruff's defaults are minimal (`E` + `F` only). Opted into more categories via
`pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "C4", "SIM"]
```

| Code | Catches |
|---|---|
| `E` | pycodestyle errors (e.g. line length) |
| `F` | Pyflakes — logic issues (unused imports, undefined names) |
| `I` | Import sorting (stdlib / third-party / local, alphabetised) |
| `B` | Bug-bear — bug-prone patterns |
| `UP` | pyupgrade — old syntax with cleaner modern forms |
| `C4` | Comprehension improvements |
| `SIM` | Simplifiable code |

The stricter rules found 8 more issues (6 auto-fixable):
- `I001` — imports un-sorted → auto-fixed
- `UP045` — `Optional[str]` → `str | None` (modern syntax) → auto-fixed
- `UP035` — `typing.Generator` → `collections.abc.Generator` → auto-fixed
- `UP017` — `timezone.utc` → `datetime.UTC` → auto-fixed
- `UP015` — redundant `"r"` in `open(path, "r")` → auto-fixed
- `E501` ×2 — lines too long → **fixed by hand** (ruff won't auto-fix, since
  breaking a line can change meaning)

### Fixing long lines — adjacent string concatenation

Python automatically joins strings sitting next to each other inside `()`:

```python
print(
    f"  Thresholds  : H > {ENTROPY_LIMIT} | "
    f"Len > {LENGTH_LIMIT} | Z > {ZSCORE_LIMIT}"
)
```

Two `f`-strings, no comma → Python glues them into one. Each piece needs its
own `f` prefix or that half stops interpolating `{...}`.

Note: 88 is a *convention*, not a law. Alternatives were to raise
`line-length` in config or `# noqa` the lines. Fixed them to keep the standard
limit — the tool serves you, not the reverse.

---

## Mypy — Type Checker

Reads the type hints in your code (`-> None`, `source_ip: str | None`, etc.)
and checks the code honours them. Catches type mismatches before runtime —
e.g. passing a string where a number is expected, or an unhandled `None`.

### What it found — library stubs (not bugs)

3 errors, all one category: **missing library stubs**.

A "stub" is a separate package describing a library's types (function
signatures, no real code). Some libraries ship types built in; some don't.
Mypy was saying *"I can't verify how you use pandas/urllib3/elasticsearch
because I have no type map for them"* — **not** "your code is wrong."

(Subtle detail: `urllib3`/`elasticsearch` showed `import-not-found` because
they're installed *in the container*, not on Windows where mypy runs. The real
runtime is Docker; the Windows env only has the dev tools.)

### Fix — ignore missing imports for third-party libs

Standard professional practice: type-check *my* code, not the libraries'.
Added to `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["pandas.*", "urllib3.*", "elasticsearch.*"]
ignore_missing_imports = true
```

Result: `Success: no issues found in 12 source files`. No real type errors
surfaced — the Week 1 code had honest, consistent annotations to begin with.

---

## Commands Reference

```powershell
# Always run from the engine/ directory (where pyproject.toml lives)
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor\engine

# --- Ruff ---
py -m ruff version                    # confirm installed
py -m ruff check .                    # LINT: find problems (read-only)
py -m ruff check --fix .              # LINT: apply safe auto-fixes ([*] items)
py -m ruff format --check --diff .    # FORMAT: preview changes (read-only)
py -m ruff format .                   # FORMAT: apply layout changes

# --- Mypy ---
py -m mypy --version                  # confirm installed
py -m mypy src                        # type-check the package
py -m mypy --install-types            # fetch available stub packages (alt approach)
```

**Habit learned:** preview before applying. `--check`/`--diff` (format) and
plain `check` (lint) show what *would* change before `--fix`/`format` writes
anything. Then `git diff` to read what actually changed. Same discipline that
would have caught the unsaved-file incident in Week 2.

### `py` vs `python`

On this Windows machine `python` triggers the Microsoft Store shortcut (no real
Python). `py` is the official Windows Python launcher and works. Use `py -m ...`
for everything. (The project's *runtime* Python is inside Docker; these dev
tools run on the Windows `py`.)

---

## What "Points to the toml" Actually Means

Common confusion clarified: ruff/mypy **check the `.py` files**, not the
`pyproject.toml`. They *read* the toml once at startup as a rulebook (which
rules are on, line length, what to ignore), then scan the actual code using
those settings. Analogy: a building inspector reads the building code, then
inspects the house — not the code book. Config in the toml means the rules
travel with the repo, so anyone (or CI) who runs the tools gets identical
behaviour.

---

## Git History This Session (3 focused commits)

Kept separate by concern — clean history is itself a portfolio signal:

```
Apply ruff: fix undefined logger bug, format codebase
Configure mypy: ignore missing stubs for third-party libs
Enable stricter ruff rules (I,B,UP,C4,SIM); modernise syntax, fix line lengths
```

---

## Week 3 Remaining (next sessions)

| Item | Notes |
|---|---|
| **pytest** | Its own full session — writing tests is a new skill, don't rush it. Start with pure-logic functions: entropy calc, `parse_line()`. |
| **GitHub Actions** | After pytest works locally. CI just *runs* ruff + mypy + pytest automatically on every push — pointless to automate before understanding each by hand. |
| Rotation-aware `LogReader` | Code change (Week 2 Bug 2). Write a pytest that reproduces the bug first, then fix. |
| Retry-on-missing-file at startup | Code change (Week 2 Bugs 1 & 6). |
| Alert deduplication | 4 alerts per query (A+AAAA × both legs). |

**Order rationale:** learn one tool deeply before the next. ruff (gentlest,
instant feedback) → mypy (builds on it) → pytest (new skill, own session) →
CI (automates the rest). Done across sessions in the order that teaches the
tools rather than installing them past you.

---

*Companion files: ENGINE_NOTES.md, ZEEK_NOTES.md, BIND9_NOTES.md.*
