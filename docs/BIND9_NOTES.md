# Bind9 Containerisation Notes

> Captured 9 June 2026, after diagnosing and fixing Bind9 in Docker.
> Complements WEEK2_NOTES.md — focus here is on the lessons specific to running DNS infrastructure in containers.

---

## What Worked

- ✅ Bind9 9.18 container running and healthy
- ✅ Custom config mounted via bind mount (`infra/bind9/named.conf.options`)
- ✅ Successfully forwarding queries through upstream resolvers
- ✅ Resolving real domains from Windows host via `127.0.0.1`

---

## Key Concept — Container Images Are Intentionally Minimal

The `ubuntu/bind9` image ships **only the Bind9 server binary**. No `dig`, no `host`, no `nslookup`, no `ping`. This is intentional and is the production-correct approach.

**Why minimal images matter:**

| Reason | Detail |
|---|---|
| Smaller size | Less to download, faster startup |
| Smaller attack surface | An attacker inside has fewer tools to pivot |
| Forces discipline | You learn proper container debugging instead of relying on shell tools |

**How to debug minimal containers:**

| Need | Solution |
|---|---|
| Test DNS resolution | Query from host: `Resolve-DnsName name -Server 127.0.0.1` |
| Check config syntax | Use server-side tools: `named-checkconf` |
| Verify ports open | `docker compose ps` shows port mappings |
| See live activity | `docker compose logs -f bind9` |

---

## Key Concept — DNS Interception Is Common

When `1.1.1.1` and `8.8.8.8` did not work, the explanation was: **the network blocks outbound port 53 to public resolvers**.

This is the norm, not the exception, in:
- University networks (your case — IPs in the `163.167.80.0/24` range belong to a UK organisation)
- Corporate networks
- Many home ISPs (notably UK and EU ISPs)
- Hotels, cafes, public Wi-Fi

**Real-world implication for security work:**

DNS interception is exactly the threat **DNS-over-HTTPS (DoH)** was designed to defeat. By tunnelling DNS inside HTTPS to port 443, queries bypass port 53 interception entirely. This is why DoH adoption has accelerated since 2018 and why your project's future enhancement to inspect DoH (FE5) matters.

---

## Key Concept — Forwarders vs Recursion

```
forwarders { 163.167.80.15; 140.97.4.12; };
forward only;
```

| Mode | Behaviour |
|---|---|
| `forward only` | Always forward to upstreams, never try to resolve recursively yourself |
| `forward first` (default) | Try upstreams first, fall back to recursive resolution if they fail |
| No `forwarders` | Resolve everything yourself starting from root servers |

We chose `forward only` because:
- Root servers (`.`) are unreachable from this network anyway
- It is the **enterprise standard** — corporate DNS infrastructure always forwards through known choke points
- Reduces external DNS traffic

---

## Key Concept — Bind Mounts for Configuration

In `docker-compose.yml`:

```yaml
volumes:
  - ./infra/bind9/named.conf.options:/etc/bind/named.conf.options:ro
```

This is a **bind mount** — your local file appears inside the container at a specific path.

| Aspect | Detail |
|---|---|
| Source | `./infra/bind9/named.conf.options` on your laptop |
| Destination | `/etc/bind/named.conf.options` inside container |
| `:ro` | Read-only — container cannot modify the file |

**Why this pattern matters:**
- Config lives in your git repository (versioned)
- You edit it with your normal text editor
- Container reads fresh on restart — no rebuild needed
- Separation of application (container) and configuration (mount)

This is **the 12-factor approach to configuration**. Hiring managers recognise it immediately.

---

## Lessons Worth Noting

### Lesson 1 — Always Diagnose Before Guessing

When Bind9 reported `unhealthy`, the wrong move would be googling "Bind9 unhealthy docker." The right move was:

1. `docker compose logs bind9` — see what the container is actually saying
2. `docker compose exec bind9 which dig` — verify assumptions about tools available
3. `Resolve-DnsName ... -Server 1.1.1.1` — verify the network layer works

Three commands took 30 seconds and revealed two distinct problems (missing dig + blocked outbound DNS) that each needed different fixes. Guessing would have cost hours.

### Lesson 2 — Healthchecks Must Use Tools That Exist in the Image

Initial healthcheck:
```yaml
test: ["CMD-SHELL", "dig @127.0.0.1 google.com ... || exit 1"]
```

Failed because `dig` is not installed. Lesson: **always verify your healthcheck command works inside the container before deploying.**

Fixed version uses `named-checkconf` which is guaranteed to be present:
```yaml
test: ["CMD-SHELL", "named-checkconf || exit 1"]
```

### Lesson 3 — PowerShell Treats `@` as Special

```powershell
docker compose exec bind9 dig @127.0.0.1 google.com    # FAILS in PowerShell
docker compose exec bind9 dig "@127.0.0.1" google.com  # WORKS
```

The `@` symbol triggers PowerShell variable reference syntax. Always quote arguments containing `@` when calling external commands.

### Lesson 4 — Test From Outside the Container When Possible

If you cannot verify a service from inside its container (missing tools), test it from outside. This is actually more realistic — users hit your service from outside, not from inside.

```powershell
Resolve-DnsName google.com -Server 127.0.0.1
```

Tests the same path a real client would use.

### Lesson 5 — DNSSEC Validation Is Brittle in Restricted Networks

```
dnssec-validation auto;    # Brittle when upstream resolvers strip DNSSEC
dnssec-validation no;      # Pragmatic for dev/portfolio
```

Some upstream resolvers (especially corporate or ISP-mandated) strip DNSSEC records, causing Bind9 to refuse responses. For dev/lab work, disable validation. For production, ensure your upstream supports DNSSEC and validate.

---

## Standard Bind9 Container Commands

```powershell
# Status and health
docker compose ps
docker compose logs bind9 --tail 50
docker compose logs -f bind9                 # follow live

# Config verification
docker compose exec bind9 named-checkconf    # silent = valid

# Test resolution from host
Resolve-DnsName google.com -Server 127.0.0.1

# Restart after config change
docker compose restart bind9

# Force full recreation (image change, healthcheck change)
docker compose up -d --force-recreate bind9
```

---

## Portfolio Talking Points (For Interviews)

When discussing this project, you can speak about:

> "I deployed Bind9 as a containerised DNS resolver and immediately hit a real-world network constraint: outbound port 53 to public resolvers was blocked. I diagnosed this through container logs and host-level testing with `Resolve-DnsName`, then adapted the configuration to forward through the network's own resolvers using `forward only` mode. This is actually the enterprise pattern — corporate DNS is rarely fully recursive — so the workaround became the production-correct design. The same network behaviour explains why DNS-over-HTTPS (DoH) adoption has accelerated, which is a documented future enhancement for the detection engine."

This shows:
- Practical troubleshooting skill
- Network awareness (relevant to CCNA)
- Understanding of real enterprise topology
- Connection between operational reality and security architecture

---

*Append to PORTFOLIO_NOTES.md → Lessons section, or keep as standalone reference.*
