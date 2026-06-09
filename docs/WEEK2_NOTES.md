# Week 2 Notes — Containerisation Progress

> Captured mid-session on 4 June 2026, after successful first container build and run.
> Append these to the main PORTFOLIO_NOTES.md when convenient.

---

## What Worked Today

- ✅ Container `dns-monitor:3.0.0` builds clean (87.6 MB, multi-stage)
- ✅ Container runs, prints startup banner, imports work, Elasticsearch client initialises
- ✅ Six clean commits in git history — atomic and descriptive
- ✅ All three new files tracked: `Dockerfile`, `.dockerignore`, `pyproject.toml`

The `FileNotFoundError` on `/logs/dns.log` is **expected behaviour** — there is no Zeek inside this container yet. We solve it next with docker-compose.

---

## Lesson 1 — Never Edit the Same Code in Two Places

**What happened:** I had a typo in `record.py` (`annotation` missing the `s`). I fixed it directly on Ubuntu with `sed`. Git on Windows never knew about the fix. Eventually the two copies diverged and I had to commit the fix days later.

**The rule going forward:**

| Environment | Role |
|---|---|
| Windows | Development — edit code, commit, push |
| Ubuntu | Deployment target — pull only, never edit |

**Once Docker is finished this week, Ubuntu is no longer needed.** Docker handles the runtime so Windows alone covers both dev and run.

---

## Lesson 2 — Always Verify State Before Building On Top

Senior engineers never assume their environment is the way they left it. **Verify, then build.**

### The 5-Check Session-Start Routine

Run these every time you start work, before touching new code:

```powershell
# 1. Is Docker Desktop running?
docker version

# 2. Am I in the right directory? Any uncommitted work from last time?
cd <project-path>
git status

# 3. What was the last thing I did?
git log --oneline -5

# 4. Do my key files still exist with content?
ls <important-files>

# 5. Are previously-built artefacts still there?
docker images <my-image>
```

Each check is 10 seconds. Total: under a minute. Saves hours of confused debugging.

---

## Lesson 3 — Commit Atomically with Meaningful Messages

**Bad:**
```
git commit -m "stuff"
git commit -m "updates"
```

**Good (what we did today):**
```
8330d35 Fix import errors in __main__.py and record.py
7dee5c9 Add Dockerfile, .dockerignore, and pyproject.toml for containerisation
```

**The rule:** One logical change per commit. Message states *what changed* in present tense. Hiring managers read your git log — clean history signals a careful engineer.

---

## Lesson 4 — Docker Multi-Stage Builds Cut Image Size by 80%

The Dockerfile we wrote uses two stages:

- **Stage 1 (builder)** — heavy, includes `build-essential` for compiling Python packages, ~800 MB
- **Stage 2 (runtime)** — lean, just Python + our installed packages copied from stage 1, **87.6 MB final**

Stage 1 is discarded after the build. Stage 2 ships to production. This pattern is standard at every serious company.

---

## Lesson 5 — Containers Run as Non-Root by Default in Production

Our Dockerfile creates a `dnsmonitor` user and switches to it before `CMD`. If anything inside the container is exploited, the attacker has no root inside the container.

```dockerfile
RUN groupadd --system dnsmonitor && \
    useradd --system --gid dnsmonitor --create-home dnsmonitor
USER dnsmonitor
```

Hiring managers explicitly check for this in interview code reviews.

---

## Lesson 6 — Environment Variables for Configuration, Not Code

Our Dockerfile sets `ENV` defaults:

```dockerfile
ENV ES_HOST=https://elasticsearch:9200 \
    ENTROPY_LIMIT=4.0
```

These can be overridden at runtime without rebuilding:

```powershell
docker run -e ENTROPY_LIMIT=4.5 dns-monitor:3.0.0
```

This is the **12-factor app** methodology. Same image runs in dev, staging, prod — only the env vars change.

---

## Where We Are in the 6-Week Plan

| Week | Focus | Status |
|---|---|---|
| 1 | Foundation reset | ✅ Done |
| 2 | Containerisation | 🔄 In progress — engine container done, docker-compose next |
| 3 | Testing & code quality | Future |
| 4 | Observability stack | Future |
| 5 | Cloud deployment | Future |
| 6 | Polish & promotion | Future |

---

## Next Steps — Clear Path Forward

### Immediate next step (this session)

**Build `docker-compose.yml`** in the repository root. This file orchestrates the whole stack:

```
docker-compose.yml will define:
├── bind9 service       (DNS resolver)
├── zeek service        (network monitor)
├── elasticsearch       (database)
├── kibana              (dashboard)
└── dns-monitor         (your engine — already containerised)
```

Plus shared networks and volumes for log files.

Single command to start everything: `docker compose up -d`  
Single command to stop everything: `docker compose down`

### After docker-compose works

1. Test full stack — send DNS queries, see alerts in Kibana
2. Document deployment in README
3. Commit and push
4. Tag the repository as `v2.0.0`

### Week 3 onwards

1. Write `pytest` tests for the four detection rules
2. Add GitHub Actions for CI
3. Add Prometheus metrics endpoint
4. Deploy to AWS Free Tier with Terraform

---

## Quick Reference — Standard Commands

```powershell
# Verify container builds and runs
docker build -t dns-monitor:3.0.0 ./engine
docker run --rm dns-monitor:3.0.0

# Inspect a running container
docker ps
docker logs <container-id>

# Clean slate
docker compose down -v   # stops everything and deletes volumes
docker system prune -a   # removes all stopped containers and unused images

# Git workflow
git status
git add <files>
git commit -m "Descriptive message in present tense"
git push origin main
```

---

*End of Week 2 mid-session notes. Update when docker-compose is finished.*
