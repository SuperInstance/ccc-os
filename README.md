# CCC-OS — Autonomous Fleet Monitoring

CCC-OS monitors fleet services, triages signals, and generates decision-ready output without human bottlenecks.

It watches GitHub discussions, fleet health, and Zero-Connectivity feeds, applies a codified rubric to decide what matters, and produces prioritized task queues and presentation decks.

---

## Install

```bash
git clone https://github.com/SuperInstance/ccc-os.git
cd ccc-os
pip install -e .

# Verify gh is authenticated (needed for discussion monitor)
gh auth status
```

---

## Quick Start

```bash
# Print fleet status table
ccc-os

# JSON output for CI pipelines
ccc-os --json

# Watch mode: recheck every 15 minutes
ccc-os --watch 900

# Run a specific monitor
ccc-os --monitor breeder

# Start the REST API server
ccc-os --serve --config config.yaml

# Custom config file
ccc-os --config /path/to/config.yaml

# Debug logging
ccc-os --log-level DEBUG --json
```

### Metrics Endpoint (`/metrics`)

CCC-OS exposes status as JSON for scraping. Pipe `--json` to your metrics collector:

```bash
ccc-os --json
```

For Prometheus, export via cron every 5 minutes:

```bash
*/5 * * * * cd /opt/ccc-os && ccc-os --json > /var/lib/prometheus/ccc-os.json
```

### Plugin API Quickstart

```python
from ccc_os.registry import register_monitor

def check_my_agent():
    return {"ok": True, "diversity": 0.75}

register_monitor("my_agent", check_my_agent, priority="P1")
```

See `docs/PLUGIN_API.md` for the full API reference, `docs/SCALING.md` for the scaling guide and multi-node setup, and `RUNBOOK.md` for 3-AM troubleshooting.

### Scale

See `docs/SCALING.md` for how to scale CCC-OS across multiple nodes.

### Deploy

```bash
# Docker
docker build -t ccc-os .
docker run ccc-os

# Kubernetes
kubectl apply -f k8s/ccc-os-deployment.yaml
```

---

## Configuration (YAML)

Create `config.yaml`:

```yaml
ccc_os:
  data_dir: ./data
  log_level: INFO

  monitors:
    breeder:
      enabled: true
      interval: 900       # check every 15 min
    discussion5:
      enabled: true
      interval: 300       # check every 5 min
    zc:
      enabled: true
      interval: 300
    health:
      enabled: true
      interval: 300
    constraint:
      enabled: true
      interval: 600       # check every 10 min

  notifications:
    discord_webhook: ""                        # or ${DISCORD_WEBHOOK}
    telegram_bot_token: ""                     # or ${TELEGRAM_BOT_TOKEN}
    telegram_chat_id: ""
    webhook_url: ""
    alert_file: ""                             # JSONL file path

  fleet_bus:
    enabled: auto                             # auto-detect fleet event bus

  api:
    host: "0.0.0.0"
    port: 14001

  rubric:
    weights:
      blocker: 10.0
      breakthrough: 8.0
      architecture: 6.0
      numbers: 5.0
      routine: 0.5

  health_services:
    - name: MUD
      host: 147.224.38.131
      port: 4042
      path: /status
    - name: Arena
      host: 147.224.38.131
      port: 4044
      path: /stats
    - name: PLATO Gate
      host: 147.224.38.131
      port: 8847
      path: /rooms

  zc_log_dir: ""                              # or path to ZC log directory
  discussion_repo: SuperInstance/SuperInstance
  discussion_number: 5
```

Environment variable substitution works: use `${VAR_NAME}` in any string value.

Load it:

```python
from ccc_os.config import Config, get_config

# From file
config = get_config("config.yaml")

# Access values
config.api_port                      # 14001
config.data_dir                      # Path("./data")
config.log_level                     # "INFO"
config.monitor_config("breeder")     # {"enabled": true, "interval": 900}
config.notification_channels()       # {"discord_webhook": "...", ...}
config.health_services()             # [{"name": "MUD", ...}, ...]
config.rubric_weights                # {"blocker": 10.0, ...}
```

---

## The 5 Monitors

### 1. Breeder Monitor

Watches breeder diversity scores:

```python
from ccc_os.monitors.breeder import BreederMonitor
from ccc_os.config import get_config

monitor = BreederMonitor(get_config())
result = monitor.check()
# {"ok": True, "diversity": {"current": 0.92, "threshold": 0.35},
#  "alerts": [...]}
```

### 2. Discussion #5 Monitor

Polls `SuperInstance/SuperInstance/discussions/5` via `gh`, diffs against last state, triages:

```python
from ccc_os.monitors.discussion5 import DiscussionMonitor

monitor = DiscussionMonitor(get_config())
result = monitor.check()
# {"ok": True, "new_comments": 3, "triage": {"ACT_NOW": 1, "TRACK": 2}}
```

### 3. Zero-Connectivity (ZC) Monitor

Watches ZC log directories for new entries:

```python
from ccc_os.monitors.zc import ZCMonitor

monitor = ZCMonitor(get_config())
result = monitor.check()
```

### 4. Health Monitor

Probes configured fleet services and reports up/down status:

```python
from ccc_os.monitors.health import HealthMonitor

monitor = HealthMonitor(get_config())
result = monitor.check()
# {"ok": True, "services_up": 16, "services_down": 2,
#  "details": [{"name": "MUD", "ok": True, ...}, ...]}
```

### 5. Constraint Monitor

Checks fleet constraint compliance:

```python
from ccc_os.monitors.constraint import ConstraintMonitor

monitor = ConstraintMonitor(get_config())
result = monitor.check()
```

### Register Custom Monitors

```python
from ccc_os.registry import register_monitor, run_all_monitors

def check_my_service():
    # ... return dict with ok, alerts, etc.
    return {"ok": True, "details": "service is running"}

register_monitor("my_service", check_my_service, priority="P1")

# Run all registered monitors
status = run_all_monitors()
# {"monitors": {"breeder": {...}, "my_service": {...}}, "alerts": [...]}
```

---

## Decision Rubric

The rubric decides what to do with any input. First match wins, no deliberation.

```python
from ccc_os.rubric import Input, Rubric, decide

rubric = Rubric()

# Breakthrough finding
inp = Input(
    source="discussion5",
    title="CPU Breakthrough",
    body="5.5x faster ARM64 inference",
    is_breakthrough=True,
    has_numbers=True,
)
result = rubric.score(inp)
# Decision(decision="TELL_NOW", confidence=Confidence.HIGH,
#          score=8.0, matched_rule="breakthrough", explanation="...")

# Routine status
inp = Input(source="health", title="All services up", body="...",
            is_routine_status=True)
result = rubric.score(inp)
# Decision(decision="IGNORE", ...)

# Custom weights via config
rubric = Rubric(weights={"blocker": 15.0, "breakthrough": 10.0, "routine": 0.1})
```

| Rule | Decision |
|------|----------|
| Blocker on publishing path | TELL_NOW |
| Breakthrough >5x | TELL_NOW |
| Architecture affecting ≥2 repos | TELL_NOW |
| FM asks for Casey | TELL_NOW |
| New benchmark with numbers | TELL_NOW |
| Architecture change, limited scope | LOG |
| Routine status | IGNORE |
| Default | LOG |

---

## Notifications

Multi-channel: Discord, Telegram, file, and generic webhooks.

```python
from ccc_os.notifier import Notifier, Notification, DiscordChannel, TelegramChannel, FileChannel

notifier = Notifier()
notifier.add_channel(DiscordChannel(webhook_url="https://discord.com/api/webhooks/..."))
notifier.add_channel(TelegramChannel(bot_token="123:ABC", chat_id="456"))
notifier.add_channel(FileChannel("/var/log/ccc-os/alerts.jsonl"))

# Send to all channels
results = notifier.notify(Notification(
    title="Fleet Alert",
    body="Arena service is down",
    severity="critical",   # info, warning, critical
))
# {"discord": True, "telegram": True, "file": True}

# Convenience method
notifier.notify_simple("Health Check", "All services up", severity="info")

# Or create from config dict
notifier = Notifier.from_config(
    config.notification_channels(),
    config.data_dir,
)
```

---

## Deck Generation

Fill-in-the-blank presentation decks:

```python
from ccc_os.deck import benchmark_finding, architecture_decision, fleet_status

# Benchmark deck
deck = benchmark_finding(
    title="CPU Backend 5.5x Faster",
    context="ARM64 inference backend rewritten with SIMD",
    numbers="5.5x vs GPU baseline, 2.3x vs previous CPU",
    implication="CPU-first deployments now viable for real-time",
    action="Update deployment guide for ARM64 recommendation",
    next_step="Run full regression suite + publish numbers",
)
print(deck)  # Markdown, ready to paste

# Architecture decision deck
deck = architecture_decision(
    title="Switch to JSONL Storage",
    problem="SQLite requires setup and isn't portable",
    options=["Keep SQLite", "Switch to JSONL", "Use both"],
    recommendation="Switch to JSONL",
    risk="No ACID guarantees",
    timeline="1 sprint",
)

# Fleet status deck
deck = fleet_status(
    up=17,
    down=1,
    new_tiles=42,
    blockers=["Arena service down"],
)
```

---

## REST API

```bash
# Start the API server
ccc-os --serve

# Or programmatically
```

```python
from ccc_os.api import run_api_server

server = run_api_server("0.0.0.0", 14001, background=True)
```

### Endpoints

```bash
# Run all monitors and return combined status
curl http://localhost:14001/status
# {
#   "monitors": {
#     "breeder": {"status": {...}, "priority": "P0", "ok": true},
#     "discussion5": {"status": {...}, "priority": "P0", "ok": true},
#     ...
#   },
#   "alerts": [],
#   "checked_at": "2026-05-25T08:00:00+00:00"
# }

# Get alert history
curl http://localhost:14001/alerts
# {"alerts": [...], "count": 3}

# Get current task queue
curl http://localhost:14001/tasks
# {"tasks": [...], "count": 5}

# List registered monitors
curl http://localhost:14001/monitors
# {"monitors": [{"name": "breeder", "priority": "P0"}, ...], "count": 5}

# Test the rubric against custom input
curl -X POST http://localhost:14001/rubric/test \
  -H "Content-Type: application/json" \
  -d '{
    "source": "discussion5",
    "title": "New benchmark",
    "body": "5x faster inference on ARM64",
    "is_breakthrough": true,
    "has_numbers": true
  }'
# {
#   "decision": "TELL_NOW",
#   "confidence": "high",
#   "score": 8.0,
#   "matched_rule": "breakthrough",
#   "explanation": "Breakthrough detected with quantitative evidence"
# }

# Force a monitor run
curl -X POST http://localhost:14001/monitors/run
# Same output as /status

# Health check
curl http://localhost:14001/health
# {"status": "ok", "version": "2.0.0"}
```

---

## Orchestrator

The orchestrator ties everything together: run all monitors → apply rubric → generate task queue → notify.

```python
from ccc_os.orchestrator import Orchestrator
from ccc_os.config import get_config

orch = Orchestrator(config=get_config("config.yaml"))

# Register monitors
from ccc_os.monitors.breeder import BreederMonitor
from ccc_os.monitors.health import HealthMonitor
# ... etc.

# Run the full pipeline
result = orch.run()
# {
#   "monitors": {...},
#   "alerts": [{...rubric_score: 8.0, rubric_rule: "breakthrough", ...}],
#   "tasks": [{...priority: 1, title: "...", action: "Review immediately"}, ...],
#   "elapsed_seconds": 1.23,
#   "timestamp": "2026-05-25T08:00:00+00:00"
# }

# Task queue saved to output/task_queue.json
# Alerts sent via configured notification channels
```

Or via cron:

```bash
# Run every 15 minutes
*/15 * * * * cd /path/to/ccc-os && ccc-os --json >> output/cron.log 2>&1
```

---

## Security

### Signed Releases

CCC-OS releases are tagged and signed. Each release commit is signed via GitHub's commit signing infrastructure. To verify:

```bash
git verify-commit <commit-hash>
```

See `SIGNING.md` for the full release signing policy and key management.

---

## Architecture

```
ccc_os/
├── __init__.py            # Version
├── __main__.py            # CLI entry point
├── config.py              # YAML config + env var resolution
├── registry.py            # Pluggable monitor registry
├── rubric.py              # Decision rubric (Input → Decision)
├── deck.py                # Presentation deck templates
├── notifier.py            # Multi-channel notifications
├── orchestrator.py        # Full pipeline: monitors → rubric → tasks
├── api.py                 # REST API (stdlib http.server)
├── fleet_bridge.py        # Fleet event bus bridge
└── monitors/
    ├── base.py            # Base monitor class
    ├── breeder.py         # Breeder diversity monitor
    ├── discussion5.py     # GitHub Discussion #5 monitor
    ├── zc.py              # Zero-Connectivity monitor
    ├── health.py          # Fleet service health monitor
    └── constraint.py      # Constraint compliance monitor
```

```
Pipeline: Input → Rubric → Decision → Output

┌──────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│ Monitors  │ ──→ │ Rubric   │ ──→ │ Decision  │ ──→ │ Output   │
│ (5 types) │     │ (rules)  │     │ (TELL_NOW │     │ Task Q   │
│           │     │          │     │  LOG      │     │ Decks    │
│           │     │          │     │  IGNORE)  │     │ Alerts   │
└──────────┘     └─────────┘     └──────────┘     └──────────┘
```

---

## Design Principles

| Principle | How it works |
|-----------|-------------|
| Monitor, don't poll | System auto-checks on schedule; human never asks "what's new?" |
| Decide with rules, not judgment | Rubric is a predicate list — first match wins, evaluated in milliseconds |
| Generate, don't compose | Every output is template-driven — fill in data, not write prose |
| State-change alerting only | No noise for steady state; alerts fire on transitions |
| Graceful degradation | Missing dependencies (psutil, event bus) never break checks |

---

## Related

| Repo | What |
|------|------|
| [cocapn-health](https://github.com/SuperInstance/cocapn-health) | Fleet service health checking |
| [cocapn-plato](https://github.com/SuperInstance/cocapn-plato) | PLATO tile engine + SDK |
| [cocapn-glue-core](https://github.com/SuperInstance/cocapn-glue-core) | Binary wire protocol |

---

*Built by CCC, Fleet I&O Officer.*

Part of the [SuperInstance OpenConstruct](https://github.com/SuperInstance/OpenConstruct) ecosystem.
