# DNS Security Monitor — Personal Notes & Reference

> Written 2 June 2026 after successfully refactoring the engine into a proper Python package.
> These notes consolidate what I learned during the portfolio transformation.

---

## 1. Project Snapshot

| Aspect | Detail |
|---|---|
| Project | DNS Security Monitor (refactored from CS6P05 final year project) |
| GitHub | github.com/YOURUSERNAME/dns-sec-monitor |
| Status | Modular package, runs via `python3 -m dns_monitor` |
| Lab environment | Ubuntu Server VM (192.168.201.10) + Windows host |
| Python | 3.12 inside virtual environment `dns-project-env` |

---

## 2. The Project Folder Structure I Built and Why

```
dns-sec-monitor/                  ← Git repository root (.git lives here)
├── README.md                     ← Hiring manager scans this in 60 seconds
├── LICENSE                       ← MIT — required for portfolio code
├── .gitignore                    ← Tells git what to exclude
├── docs/                         ← Architecture diagrams (.drawio files)
├── infra/                        ← Operational scripts and configs
│   └── scripts/                  ← start_dns_lab.sh, stop_dns_lab.sh
└── engine/                       ← The application
    └── src/
        └── dns_monitor/          ← The Python PACKAGE
            ├── __init__.py       ← Marker — says "this is a package"
            ├── __main__.py       ← Entry point for python -m dns_monitor
            ├── config.py         ← All environment variables, one source of truth
            ├── core/
            │   ├── __init__.py   ← Sub-package marker (empty)
            │   ├── record.py     ← DNSRecord dataclass
            │   └── orchestrator.py  ← DNSEngine — wires everything together
            ├── ingestion/
            │   ├── __init__.py
            │   └── log_reader.py    ← Reads Zeek's dns.log
            ├── detection/
            │   ├── __init__.py
            │   └── engine.py     ← DetectionEngine — the 4 statistical rules
            └── reporting/
                ├── __init__.py
                └── shipper.py    ← AlertShipper — sends to CSV/HTML/Elasticsearch
```

**Why this structure matters:** This is the standard Python package layout used by every professional project. Hiring managers recognise it on sight. The separation into `core/`, `detection/`, `ingestion/`, `reporting/` mirrors the architectural layers — and means any single piece can be tested or replaced independently.

---

## 3. Key Concept — What `__init__.py` Actually Does

The `__init__.py` file is **not where your code goes**. It is a marker file that tells Python "this folder is a package, not just any folder."

- Empty `__init__.py` = perfectly fine for most cases
- The actual code lives in separate `.py` files alongside it (record.py, log_reader.py, etc)
- This was confusing at first because the name sounds important. It is important — but only as a marker

---

## 4. Key Concept — Why Imports Look Like `from dns_monitor.config import X`

Python builds import paths from folder structure:

```python
from dns_monitor.config import ZEEK_LOG
#    └────────┘ └───┘  └────────┘
#    package  module   variable
```

- `dns_monitor` = the package folder
- `config` = the file `config.py` inside it (no `.py` suffix in imports)
- `ZEEK_LOG` = the variable defined inside that file

For nested packages:

```python
from dns_monitor.core.record import DNSRecord
```

Reads as: "from the package `dns_monitor`, the sub-package `core`, the module `record`, import the class `DNSRecord`."

This is called **absolute import** — it works from anywhere as long as the package can be found.

---

## 5. Key Concept — `__main__.py` and `python -m`

`__main__.py` is special. When you run:

```bash
python3 -m dns_monitor
```

Python finds the package `dns_monitor`, looks for `__main__.py` inside it, and runs that file. This is **the modern way to make a Python package executable**. Tools like `pip`, `pytest`, and `black` all work this way.

Why this matters for portfolio:
- Shows you understand Python packaging
- Cleaner than running `python some_script.py`
- Allows future installation via `pip install .` so users can run `dns-monitor` as a command

---

## 6. Key Concept — Configuration via Environment Variables (12-Factor)

In `config.py`:

```python
ENTROPY_LIMIT: float = float(os.getenv("ENTROPY_LIMIT", "4.0"))
```

Reads: "Get the environment variable `ENTROPY_LIMIT`. If it does not exist, use `"4.0"` as default. Convert to float."

**Why this matters:**
- Change thresholds without editing code: `ENTROPY_LIMIT=4.5 python3 -m dns_monitor`
- Secrets like `ES_PASS` never get committed to git
- Same code runs in dev, staging, production with different env vars
- This is the **12-factor app methodology** — table stakes for cloud roles

---

## 7. Key Concept — Logging vs Print

Old code:
```python
print(f"[+] ELK indexed: {res['result']}")
```

New code:
```python
logger.info("ELK indexed: %s", res["result"])
```

Logging gives you:
- Automatic timestamps and log levels (INFO, WARNING, ERROR)
- Can be redirected to files, syslog, or aggregators (Splunk, ELK)
- Standard for any production Python application
- Hiring managers immediately see "this person writes real code"

The startup banner stays as `print()` because it is a one-time visual element, not a log event. Hybrid approach was the right choice.

---

## 8. Key Concept — Type Hints

```python
def calculate_entropy(self, text: str) -> float:
```

- `text: str` = this parameter must be a string
- `-> float` = this function returns a float

Why bother:
- VS Code autocomplete becomes accurate
- Tools like `mypy` catch bugs before you run the code
- Documentation built into the function signature
- Modern Python standard — signals senior-level practice

---

## 9. Critical Lessons Learned the Hard Way

### Lesson 9.1 — Always Verify Where the Git Repository Boundary Is

I made the mistake of creating `engine/`, `docs/`, `infra/` *outside* the cloned repo folder. Git only tracks what is **inside** the folder containing the hidden `.git` directory.

**How to always check:**
```bash
cd /path/to/your/project
ls -la           # if you see .git folder, you are at the root
git rev-parse --show-toplevel    # prints the repo root path
```

### Lesson 9.2 — PowerShell vs Bash Commands

| Task | PowerShell (Windows) | Bash (Ubuntu) |
|---|---|---|
| Create empty file | `New-Item -ItemType File path` | `touch path` |
| Set env variable | `$env:VAR = "value"` | `export VAR="value"` |
| List files | `dir` or `Get-ChildItem` | `ls -la` |
| Print text | `Write-Host "text"` | `echo "text"` |

### Lesson 9.3 — Read Tracebacks Bottom to Top

Python error tracebacks read **bottom up**:
1. Bottom line = what went wrong (the error message)
2. Line above = the file and line number
3. Above that = how Python got there (the call chain)

Example I hit:
```
SyntaxError: future feature annotation is not defined
  File "record.py", line 4
    from __future__ import annotation
```

The error said "annotation is not defined" — the fix was adding the missing `s` to make it `annotations`. One character.

### Lesson 9.4 — `python` vs `python3` on Ubuntu

Ubuntu 22.04+ ships with only `python3` by default. Bare `python` does not exist. Inside an activated virtual environment, `python` usually works (the venv creates a symlink). Always safer to use `python3` explicitly.

### Lesson 9.5 — Service Startup Order Matters

The engine crashed because Zeek was not running yet — the `dns.log` file did not exist. In production this is solved by:
- Bash scripts with proper sequencing (current solution)
- Docker Compose `depends_on` + `healthcheck` (next phase)
- Code-level retry logic with backoff (could add now)

---

## 10. Standard Commands I Use Daily

### Running the engine
```bash
source ~/dns-project-env/bin/activate
cd ~/dns-sec-monitor/engine/src
export ES_PASS="dns99server"
python3 -m dns_monitor
```

### Git workflow (Windows)
```powershell
cd C:\Users\YourName\DNS-Project\dns-sec-monitor
git status                    # what changed?
git add .                     # stage all changes
git commit -m "message"       # save snapshot locally
git push origin main          # send to GitHub
```

### Git workflow (Ubuntu)
```bash
cd ~/dns-sec-monitor
git pull origin main          # get latest changes from GitHub
```

### Generating test traffic from Ubuntu Desktop
```bash
# Normal — should NOT alert
dig @192.168.201.10 google.com

# High entropy — SHOULD alert
dig @192.168.201.10 aGVsbG8td29ybGQtdGhpcy1pcy1hLXRlc3Q.evil-domain.com

# Long query — SHOULD alert
dig @192.168.201.10 this-is-a-very-long-subdomain-exceeding-fifty-characters.example.com

# Frequency spike — SHOULD alert after ~10 queries
for i in {1..20}; do dig @192.168.201.10 repeated-query.com; done
```

### Verifying Elasticsearch has alerts
```bash
curl -s -u elastic:dns99server -k https://localhost:9200/dns-alerts/_count?pretty
```

### Service management
```bash
sudo systemctl status elasticsearch
sudo systemctl status kibana
sudo zeekctl status
sudo zeekctl start
```

---

## 11. The Service Stack — What Talks to What

```
[dig command]
     ↓ port 53
[Bind9]
     ↓ (network traffic)
[Zeek] ───→ /opt/zeek/logs/current/dns.log (JSON)
                                ↓ (file tail)
                          [Python engine]
                                ↓
                    ┌───────────┼───────────┐
                    ↓           ↓           ↓
                  [CSV]      [HTML]    [Elasticsearch]
                                            ↓ port 9200
                                         [Kibana] ── browser ──→ Analyst
                                            (port 5601)
```

- Bind9 listens on **port 53** for DNS queries
- Zeek passively sniffs the interface, writes JSON logs
- Python engine tails the log, applies detection rules
- Elasticsearch on **port 9200** is the database (API only, not for browsers)
- Kibana on **port 5601** is the dashboard (browser-friendly)

---

## 12. The 6-Week Portfolio Plan — Where I Am

| Week | Focus | Status |
|---|---|---|
| 1 | Foundation reset — git, README, package structure | ✅ DONE |
| 2 | Containerisation — Docker, docker-compose | ⏳ Next |
| 3 | Testing & code quality — pytest, mypy, GitHub Actions | Future |
| 4 | Observability — Prometheus, Grafana | Future |
| 5 | Cloud deployment — Terraform → AWS Free Tier | Future |
| 6 | Polish — demo video, LinkedIn post, blog post | Future |

---

## 13. Future Engine Enhancements I Want to Add

Captured here so I do not forget:

1. **Graceful waiting for Zeek log** — instead of crashing if dns.log does not exist, wait with retry/backoff
2. **Better alert visual output** — use `rich` library for boxed, colour-coded terminal alerts
3. **Prometheus metrics endpoint** — `/metrics` for counters (alerts per rule, queries processed, errors)
4. **CSV rotation** — current CSV grows forever, should rotate at size/date thresholds
5. **Async Elasticsearch writes** — current sync calls add ~10ms per alert
6. **Domain whitelist (FE7)** — prevent false positives on known-good high-entropy CDN domains
7. **Machine learning classifier (FE1)** — Random Forest or LSTM trained on baseline traffic

---

## 14. Questions to Investigate Later

- How do I expose Kibana publicly when I deploy to AWS without breaking security?
- What is the right way to manage secrets in Docker vs in Kubernetes vs in AWS?
- How do I write a useful `pytest` test for the entropy calculation?
- Should I use `pydantic` instead of `dataclass` for the DNSRecord?
- What is the difference between Docker volumes and bind mounts for the log file?

---

## 15. People & Resources

- **My supervisor** — Dr Bilal Hassan (London Metropolitan University)
- **Original report** — CS6P05 final year project, submitted May 2026
- **Reference book to skip** — Old O'Reilly BIND books (outdated for security work)
- **Better resources** — Cloudflare Learning Center, RFC 9499 (DNS Terminology 2024), SANS DNS webcasts

---

## 16. Quick Self-Test — Can I Explain These?

If I can answer these in 60 seconds, I understand the project well enough for an interview:

- [ ] Why did I split the engine into a package instead of keeping a single file?
- [ ] What is the difference between `__init__.py` and `__main__.py`?
- [ ] Why use environment variables instead of hardcoded config?
- [ ] What does Shannon Entropy detect and why does H > 4.0 work?
- [ ] What is the difference between Elasticsearch and Kibana?
- [ ] Why is Zeek better than tcpdump for this project?
- [ ] What is the 12-factor app methodology?
- [ ] How do I read a Python traceback?

---

*End of notes. Update this document as the project evolves.*
