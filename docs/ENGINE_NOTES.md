# Engine Integration Notes — Sessions of 11–12 June 2026

> **Status: WEEK 2 COMPLETE. ✅**
> Full pipeline proven: client → Bind9 → Zeek → engine → Elasticsearch.
> Detection rules (Shannon entropy, NXDOMAIN) firing on real captured query
> names. Alert documents in the `dns-alerts` index with correct scores and
> categories.

---

## The Whole Story in Plain English

Connecting the Python engine to the stack surfaced **six** problems across
two sessions. Each one, simply:

### Bug 1 — Engine looked for a file behind a broken shortcut

Zeek's `logs/current` is a **symlink** (a shortcut, like a Windows shortcut).
A shortcut stores a *path*, not the file. Zeek's shortcut pointed to a folder
that exists in Zeek's container but not in the engine's container. The engine
followed it into nothing → `FileNotFoundError` → restart loop.

Also discovered: Zeek writes its **live** log to `spool/`, not `logs/`
(`logs/` only holds archived copies).

**Fix:** mount Zeek's `spool/` as the shared volume; point the engine at the
real file: `ZEEK_LOG=/logs/zeek/dns.log`. No shortcut involved.

### Bug 2 — Engine reads a deleted file without noticing (log rotation)

Every hour Zeek **rotates** logs: archives `dns.log`, starts a fresh one. In
Linux, a program that opened a file keeps the *original* even after it is
replaced. After rotation the engine sits reading a dead file while new events
go into a file it never opened. No error. Just silence.

**Workaround:** restart the engine after any Zeek restart or rotation.
**Real fix (Week 3):** rotation-aware `LogReader` — reopen when the file at
the path changes.

### Bug 3 — Zeek captured only half of every conversation (checksums)

The big one. Zeek logged transactions with **no query name**, so the engine
alerted on `"unknown"` — entropy and length rules could never fire.

**Cause — checksum offload:** every packet carries a checksum (an
error-detection number). Normally the network card fills it in as the packet
leaves. Inside Docker Desktop there is no real network card, so
locally-generated packets go out with it blank. Zeek validates checksums and
**silently discards** failures. Packets arriving from the real internet have
valid checksums and pass. Result: one-directional blindness — and the
inbound client leg (Windows → Bind9), which carries the query, was invisible.

**Fix:** one line in `infra\zeek\local.zeek`:

```zeek
redef ignore_checksums = T;
```

After this, capture showed **both legs** (client → Bind9 at `172.18.0.1`,
Bind9 → upstream at `172.18.0.3`) with full query names and richer fields
(`qtype_name`, `qclass`). Standard fix for Zeek in any Docker/VM environment.

### Bug 4 — The fix that "didn't work" was never actually applied

The most instructive failure. The checksum fix was written in session, noted
as "applied (untested)" — but `Get-Content infra\zeek\local.zeek` later showed
the line **was never saved to disk** (unsaved editor buffer). A whole retest
ran against the unfixed config and "failed", nearly killing a correct theory.

**Lessons:**
- The next-session checklist contained the exact command that would have
  caught this (`Get-Content` the file). Checklists only work when run.
- **Verify on disk → verify in container → then test.** Never trust that an
  edit happened; read it back.
- A fix that fails may simply not be deployed. Check deployment before
  abandoning the theory.

### Bug 5 — Lab broke when changing networks (eduroam → home)

`SERVFAIL` on all queries from home wifi. Bind9's forwarders were eduroam's
resolvers, which don't answer from outside the university network.

**Fix:** switched forwarders to public resolvers (`1.1.1.1`, `8.8.8.8`) in
`infra\bind9\named.conf.options` — they answer from anywhere, making the lab
portable. **Restart order matters:** Zeek lives inside Bind9's network
namespace, so always `restart bind9` *then* `restart zeek` (then engine).

**If eduroam blocks public DNS** (untested): per-environment config files
selected by a `.env` variable — `named.conf.options.${DNS_ENV:-home}` in the
compose mount. Same 12-factor pattern the engine already uses. Backlogged
until proven necessary.

### Bug 6 — Engine missed events because it starts reading at the end

`LogReader.tail()` seeks to **end of file** on open. On a fresh stack,
`dns.log` only comes into existence when the *first packet* arrives — so the
engine (restart-looping until the file exists) opens it and skips straight
past the very events that created it.

**Workaround:** it only misses events from before it attached; everything
after is caught live. **Week 3:** retry-on-missing-file at startup, and
consider reading from current position rather than seeking blindly.

---

## DNS Subtleties Learned Along the Way

- **DNSSEC / aggressive NSEC caching (RFC 8198):** Bind9 can cryptographically
  prove a name doesn't exist using cached NSEC records from signed zones (like
  `example.com`) — answering **without forwarding upstream**. Test queries
  against signed zones may never generate upstream traffic. Use unsigned zones
  (e.g. `google.com` subdomains) for capture tests.
- **Windows DNS cache:** `Clear-DnsClientCache` before tests, or use a fresh
  random name each time.
- **One lookup ≠ one packet:** Windows sends A and AAAA queries; both legs are
  captured → one test query produced **four alerts**. Correct capture, noisy
  alerting — deduplication (by `uid` or query+time-window) is Week 3 backlog.

---

## Final Working Configuration

| Piece | Setting |
|---|---|
| Zeek volume | `zeek-logs:/usr/local/zeek/spool` (live logs; survives zeekctl crash-renames) |
| Engine log path | `ZEEK_LOG=/logs/zeek/dns.log` (direct file, no symlink) |
| Engine ES | `ES_HOST=http://elasticsearch:9200` (plain HTTP in dev) |
| Engine mounts | `zeek-logs:/logs:ro` (read-only — engine is a consumer), `engine-data:/data` |
| `local.zeek` | json-logs + `redef ignore_checksums = T;` |
| Bind9 forwarders | `1.1.1.1; 8.8.8.8;` (portable across networks) |

**Proof of completion:** `dns-alerts` index contains documents with real
query strings, `entropy_score: 4.7224`, category `High Entropy + NXDOMAIN`.
Threshold note: the 43-char test name did **not** trip `LargeQuery` (limit
50) — the engine was right, the prediction was wrong. Trust the code's
arithmetic.

---

## End of Session — Graceful Shutdown

```powershell
# 1. See what changed
git status

# 2. Stage today's work
git add infra/zeek/local.zeek infra/bind9/named.conf.options docker-compose.yml docs/

# 3. Commit — Week 2 milestone
git commit -m "Fix Zeek checksum validation in Docker; switch to public DNS forwarders"

# 4. Push
git push origin main

# 5. Stop containers (volumes and data survive)
docker compose stop
```

`stop` pauses, `down` deletes containers, `down -v` deletes data too.
Overnight = `stop`.

---

## Next Session — Startup Checklist (Week 3 begins)

```powershell
# 1. Right folder, clean repo, milestone commit present
cd C:\Users\atar\Documents\DNS-Project\dns-sec-monitor
git status                  # expect: working tree clean
git log --oneline -2        # expect: checksum-fix commit on top

# 2. Verify config survived ON DISK (Bug 4's lesson — actually run this)
Get-Content infra\zeek\local.zeek          # both lines
Get-Content infra\bind9\named.conf.options # public forwarders

# 3. Start stack, wait ~60s
docker compose up -d
docker compose ps           # all 5 Up, three (healthy)

# 4. Zeek's process is alive (container "Up" does NOT prove this — PID 1 is tail)
docker compose exec zeek zeekctl status    # expect: running

# 5. Engine may be restart-looping until first packet creates dns.log —
#    this is the known Bug 6 race. Feed it a packet:
Resolve-DnsName google.com -Server 127.0.0.1
Start-Sleep -Seconds 5
docker compose ps           # engine now Up and stable

# 6. Smoke test — full pipeline in one shot (fresh random name each time)
Resolve-DnsName "<24+ random chars>.google.com" -Server 127.0.0.1
Start-Sleep -Seconds 5
docker compose logs engine --tail 5        # expect [!!] HighEntropy alert
```

---

## Week 3 Backlog (seeded by this week's bugs)

| Item | Born from |
|---|---|
| Rotation-aware `LogReader` (reopen on file change) | Bug 2 |
| Retry-on-missing-file at engine startup | Bugs 1 & 6 |
| Heartbeat logging ("processed N records") — silence ≠ health | Bug 3's invisibility |
| Alert deduplication (uid or query+window) | 4 alerts per query |
| Test eduroam vs public resolvers; `DNS_ENV` switch if needed | Bug 5 |
| Pytest cases reproducing Bugs 1, 2, 6 | the debugging itself |

---

## The Habit That Solved Everything

> **Stabilise → read the real error → form a theory → verify the fix is
> actually deployed → test with a controlled experiment → only then conclude.**

Bug 4 added the step in the middle: *verify deployment*. A correct theory
nearly died because the fix existed only in conversation, not on disk.

---

*Companion files: ZEEK_NOTES.md (PID 1, network namespaces, volume/symlink
collision), BIND9_NOTES.md. Week 3 opens with pytest/ruff/mypy/GitHub Actions.*
