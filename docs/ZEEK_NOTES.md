# Zeek Containerisation Notes

> Captured 10 June 2026, after diagnosing and fixing Zeek in Docker.
> Complements BIND9_NOTES.md and WEEK2_NOTES.md — focus here is on passive network monitoring in containers and the PID 1 lifecycle.

---

## What Worked

- ✅ Zeek container running stable, sniffing Bind9's traffic
- ✅ `network_mode: service:bind9` — shared network namespace, no host network access needed
- ✅ JSON DNS logs flowing to the `zeek-logs` volume in the exact format the Python engine parses
- ✅ Both legs of resolution visible: client → Bind9 *and* Bind9 → upstream forwarder

---

## Key Concept — Shared Network Namespaces

```yaml
zeek:
  network_mode: service:bind9
```

Normally each container gets its own network namespace (own virtual interface, own IP). This directive makes Zeek **join Bind9's namespace** instead — same `eth0`, same IP, same traffic.

| Aspect | Consequence |
|---|---|
| Zeek sees everything Bind9 sees | Passive capture without port mirroring or TAPs |
| Zeek has no `networks:` entry | It rides inside Bind9's network — cannot be on `dns-net` independently |
| `depends_on: bind9` required | The namespace must exist before Zeek can join it |
| Both query legs captured | Inbound (client → Bind9) and outbound (Bind9 → forwarder) cross the same interface |

This is the container equivalent of plugging an IDS into a SPAN port — and a direct talking point for NOC/SecOps interviews.

---

## Key Concept — PID 1 and the Container Lifecycle

**This was the root cause of the restart loop, and it is the single most important Docker concept in these notes.**

### The rule

> A container lives exactly as long as its main process (PID 1) lives.

On a normal Linux system, PID 1 is `init`/`systemd` — it boots the machine, supervises every other process, and runs until shutdown. A container has no init system. Whatever command the container starts with **becomes PID 1**, and Docker equates that process's life with the container's life:

```
PID 1 running  →  container "Up"
PID 1 exits    →  container dead — Docker kills every other process inside
```

### Why `zeekctl deploy` caused the loop

`zeekctl` is a **management tool**, like `systemctl`. Its job is to start Zeek *in the background* and then exit — which is correct behaviour on a server, and fatal in a container:

```
1. Container starts        →  zeekctl deploy becomes PID 1
2. zeekctl forks Zeek      →  Zeek runs in background, sniffing happily
3. zeekctl finishes        →  PID 1 exits
4. Docker: "PID 1 is dead" →  kills the container, including Zeek
5. restart: unless-stopped →  back to step 1, forever
```

Every cycle, Docker killed Zeek mid-flight — which is why each restart logged `creating crash report for previously crashed nodes`. Zeek never crashed on its own; it was being executed by its supervisor.

### The fix — give PID 1 something to do forever

```yaml
command: sh -c "zeekctl deploy && tail -F /usr/local/zeek/logs/current/dns.log"
```

| Part | Role |
|---|---|
| `sh -c "..."` | Shell becomes PID 1, runs both commands in sequence |
| `zeekctl deploy` | Starts Zeek in the background (as before) |
| `&&` | Only continue if deploy succeeded |
| `tail -F dns.log` | Foreground process that never exits — keeps PID 1 alive |

Bonus: because `tail` streams `dns.log` to stdout, `docker compose logs zeek` now shows live DNS events for free.

### `tail -f` vs `tail -F` — one character, one outage

| Flag | If file does not exist |
|---|---|
| `-f` | Exits with an error immediately |
| `-F` | Waits and retries until the file appears, then follows it |

`dns.log` is only created when Zeek sees its **first DNS packet** — so at container start it never exists yet. With `-f`, tail died instantly, PID 1 exited, and the loop continued *even after the real fix was in place*. `-F` is the correct flag for any log that appears asynchronously.

### How to recognise this failure pattern in future

| Symptom | Suspicion |
|---|---|
| Container restart-loops but the app's own logs show no error | PID 1 is exiting, not the app crashing |
| Logs show a clean startup repeated over and over | Same — the loop is external to the app |
| `docker compose ps` shows `Restarting (1)` with exit code 1 | Main command finished or failed — check what PID 1 actually is |

The general fixes, in order of preference:
1. Use an image whose entrypoint runs the app **in the foreground** (most official images do this)
2. Run the daemon's foreground mode directly (e.g. `zeek -i eth0` instead of `zeekctl`)
3. Chain a never-ending foreground command after the management tool (our `tail -F` approach)

---

## Key Concept — Volumes vs Symlinks

First failure of the day:

```
Error: failed to update symlink '/usr/local/zeek/logs/current': [Errno 21] Is a directory
```

Zeek's `logs/current` is a **symlink** it manages itself, repointing it to the active timestamped log directory. Mounting a volume directly onto that path forced it to be a real directory — and Zeek cannot replace a directory with a symlink.

```yaml
- zeek-logs:/usr/local/zeek/logs/current   # WRONG — collides with Zeek's symlink
- zeek-logs:/usr/local/zeek/logs           # RIGHT — mount the parent, let Zeek manage current/
```

**Rule: never mount a volume onto a path the application manages dynamically.** Mount one level up.

---

## Key Concept — Capabilities for Packet Capture

```yaml
cap_add:
  - NET_RAW      # open raw sockets — required by libpcap
  - NET_ADMIN    # set interface to promiscuous mode
```

Containers run with a restricted capability set by default. Packet sniffing needs these two. This was **not** the cause of our restart loop, but it is required for capture and is far better practice than `privileged: true`, which grants everything. Granting the two specific capabilities you need is the least-privilege approach — interviewers notice the difference.

---

## Lessons Worth Noting

### Lesson 1 — Verify Image Names; `docker search` Is the Tool

`zeekurity/zeek` does not exist. One command found the official image:

```powershell
docker search zeek    # zeek/zeek, 14 stars — the official release image
```

Never trust an image name from memory (yours or an AI's). Verify against the registry.

### Lesson 2 — Read the App's Own Logs, Not the Supervisor's Chatter

`docker compose logs zeek` showed zeekctl's noisy deploy output on loop — useless. The truth lived in Zeek's own files:

```
/usr/local/zeek/spool/zeek/stderr.log   →  "listening on eth0"  (Zeek was fine!)
```

That one line redirected the whole diagnosis from "Zeek is crashing" to "something is killing Zeek" — which led straight to PID 1.

### Lesson 3 — Stabilise the Container Before Debugging It

A crash-looping container cannot be inspected — it dies before you can exec into it. The trick:

```yaml
command: sleep infinity    # temporary — PID 1 idles forever, container stays up
```

Then exec in and run the real command manually, watching the errors live:

```powershell
docker compose exec zeek zeekctl deploy
docker compose exec zeek cat /usr/local/zeek/spool/zeek/stderr.log
```

This converts an un-debuggable loop into an interactive session. Standard incident-response technique for containers.

### Lesson 4 — Distinguish Errors From Noise

`sendmail: /usr/sbin/sendmail not found` looked alarming but was harmless — zeekctl trying to email a crash notification with no MTA installed. Chasing it would have wasted time. Always ask: *is this message the cause, or a side effect?*

### Lesson 5 — Three Stacked Failures Is Normal

| # | Failure | Fix |
|---|---|---|
| 1 | Image name did not exist | `docker search` → `zeek/zeek` |
| 2 | Volume mounted onto managed symlink | Mount parent `logs/` instead |
| 3 | PID 1 exited after `zeekctl deploy` | `tail -F` as foreground process |

Each fix exposed the next failure. This is what real infrastructure work looks like — the skill is methodical isolation, not avoiding mistakes.

---

## Graceful Session Shutdown

How to end a working session without losing state or corrupting logs.

### Standard end-of-session sequence

```powershell
# 1. Verify everything is healthy before touching anything
docker compose ps

# 2. Commit and push all work
git status
git add docker-compose.yml infra/zeek/ ZEEK_NOTES.md
git commit -m "Add Zeek sniffer via shared network namespace with Bind9"
git push origin main

# 3. Stop the stack — containers stop, volumes and images remain
docker compose stop
```

### Why `stop`, not `down`

| Command | Containers | Networks | Volumes (logs, ES data) |
|---|---|---|---|
| `docker compose stop` | Stopped, kept | Kept | Kept |
| `docker compose down` | **Removed** | **Removed** | Kept |
| `docker compose down -v` | **Removed** | **Removed** | **DELETED** |

For day-to-day pausing, `stop` is correct — next session is just `docker compose up -d` and everything resumes, including Elasticsearch data and Zeek logs. Use `down -v` only when you deliberately want a clean slate.

### Stop order and timeouts

`docker compose stop` sends SIGTERM to each container's PID 1, waits 10 seconds, then SIGKILL. Two notes:

- **Zeek**: our PID 1 is `sh`/`tail`, which dies instantly on SIGTERM. Zeek itself gets killed without flushing in-flight logs — acceptable in dev, since `dns.log` is written incrementally anyway. (Production Zeek deployments extend the timeout: `docker stop -t 90 zeek` gives zeekctl time to rotate and archive logs.)
- **Elasticsearch**: handles SIGTERM properly and flushes to disk within the default window. No action needed.

If you ever need a longer grace period for the whole stack:

```powershell
docker compose stop -t 30
```

### Next-session startup

```powershell
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor
git pull origin main
docker compose up -d
docker compose ps        # wait for all healthy before working
```

---

## Standard Zeek Container Commands

```powershell
# Status — is Zeek's own process running inside the container?
docker compose exec zeek zeekctl status

# Live DNS events (tail -F streams dns.log to container stdout)
docker compose logs -f zeek

# Generate test traffic from the host
Resolve-DnsName google.com -Server 127.0.0.1

# Inspect raw log files inside the container
docker compose exec zeek ls /usr/local/zeek/logs/current/
docker compose exec zeek tail -5 /usr/local/zeek/logs/current/dns.log

# Zeek's own diagnostics after a problem
docker compose exec zeek zeekctl diag

# Recreate after compose file changes
docker compose stop zeek
docker compose rm -f zeek
docker compose up -d zeek
```

---

## Portfolio Talking Points (For Interviews)

> "I deployed Zeek as a passive DNS sniffer by sharing Bind9's network namespace — the container equivalent of a SPAN port, requiring no privileged host access. The interesting failure was a restart loop with no errors in Zeek's own logs: `zeekctl deploy` is a management tool that backgrounds the daemon and exits, and since it was PID 1, Docker treated its exit as container death and killed Zeek with it. I stabilised the container with a temporary idle command, confirmed Zeek itself was healthy from its stderr log, then fixed the lifecycle by chaining a foreground `tail -F` on the DNS log — which also gave me live log streaming through `docker logs` for free. I granted only `NET_RAW` and `NET_ADMIN` rather than running privileged, keeping to least privilege."

This shows:
- Deep understanding of the container process model (PID 1) — a common interview question
- Methodical debugging: stabilise → inspect → isolate → fix
- Security mindset: capabilities over `privileged: true`
- Passive monitoring architecture knowledge (relevant to NOC/SOC roles)

---

*Next step: point the engine container at the `zeek-logs` volume — final integration for Week 2.*
