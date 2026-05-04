# CCC-OS — The Crab's Operating System

> *"The goal isn't to need less guidance. The goal is to need none."*

CCC-OS is the autonomous infrastructure layer that lets CCC (the Fleet I&O Officer) monitor, decide, and act without human bottlenecks. It was built in one session after Casey said: *"Get yourself there."*

## Architecture

```
┌─────────────────────────────────────────┐
│  CCC-OS Orchestrator (orchestrator.py)  │
│  Runs every 15 min via cron             │
├─────────────────────────────────────────┤
│  Inputs              │  Outputs         │
├──────────────────────┼─────────────────┤
│  Discussion #5       │  Task Queue      │
│  Fleet Health        │  Decks           │
│  ZC Feeds (planned)  │  Alerts          │
├──────────────────────┼─────────────────┤
│  Decision Rubric     │  Memory Updates  │
│  (rubric.py)         │  Bottles         │
└─────────────────────────────────────────┘
```

## Components

### 1. Discussion #5 Monitor (`monitors/discussion5_monitor.py`)

Polls `SuperInstance/SuperInstance/discussions/5` every 15 minutes.

- **Diffs** against last-known state
- **Auto-triage** into ACT_NOW / TRACK / IGNORE
- **ACT_NOW** signals: breakthrough, blocker, benchmark, architecture, certification
- **TRACK** signals: routine status, coordination, technical Q&A
- Logs to `monitors/discussion5_log.jsonl`

```bash
python3 monitors/discussion5_monitor.py
```

### 2. Decision Rubric (`rubric.py`)

Codified rules for what to do with any input. No deliberation. First match wins.

| Rule | Decision |
|------|----------|
| Blocker on publishing path | TELL_NOW |
| Breakthrough >5x | TELL_NOW |
| Architecture affecting ≥2 repos | TELL_NOW |
| FM explicitly asks for Casey | TELL_NOW |
| New benchmark with numbers | TELL_NOW |
| Routine status | IGNORE |
| Technical FM→Oracle1 question | LOG |
| Default | LOG |

```python
from rubric import Input, decide
inp = Input("discussion5", "CPU Breakthrough", "5.5x faster", is_breakthrough=True)
decision = decide(inp)  # → "TELL_NOW"
```

### 3. Deck Template System (`deck.py`)

Fill-in-the-blank presentation decks. <2 minutes from data to Markdown.

**Templates:**
- `benchmark_finding` — context, numbers, implication, action, next
- `architecture_decision` — problem, options, recommendation, risk, timeline
- `fleet_status` — up/down counts, new tiles, blockers
- `research_summary` — what learned, why matters, what to do

```python
from deck import benchmark_finding
print(benchmark_finding(
    title="CPU Beats GPU",
    context="...",
    numbers="...",
    implication="...",
    action="...",
    next_step="...",
))
```

### 4. Health Autopilot (`health/autopilot.py`)

Probes 8 fleet services every 5 minutes.

- **Alerts ONLY on state changes** (up→down or down→up)
- No noise for steady state
- Logs to `health/health_log.jsonl`

Services monitored:
- MUD (4042), Arena (4044), Grammar (4045)
- PLATO Gate (8847), PLATO Shell (8848)
- Rate-Attention (4056), Skill Forge (4057)
- Matrix Bridge (6168)

```bash
python3 health/autopilot.py
```

### 5. Orchestrator (`orchestrator.py`)

The entry point. Runs all monitors, applies rubric, generates task queue.

```bash
python3 orchestrator.py
```

Output: `output/task_queue.json` — prioritized list of items to act on.

## Installation

```bash
# Clone / copy ccc-os directory
# Requires: python3, gh (GitHub CLI authenticated)
# Cron job (runs every 15 min):
crontab -e
# Add: */15 * * * * cd /path/to/ccc-os && python3 orchestrator.py >> output/cron.log 2>&1
```

## Directory Structure

```
ccc-os/
├── monitors/
│   ├── discussion5_monitor.py
│   └── discussion5_log.jsonl
├── health/
│   ├── autopilot.py
│   └── health_log.jsonl
├── rubric.py
├── deck.py
├── orchestrator.py
├── output/
│   ├── task_queue.json
│   ├── deck-*.md
│   └── cron.log
└── README.md
```

## Success Metrics

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Discussion #5 → action | 15-30 min | <5 min | ✅ <1 min |
| Decision deliberation | 2-5 min | <30 sec | ✅ <1 sec |
| Deck generation | 10-15 min | <2 min | ✅ <1 min |
| Proactive vs reactive | ~10:90 | ~50:50 | 🔄 Building |
| Casey prompts per session | 3-5 | 0-1 | 🔄 Building |

## License

Fleet Internal — SuperInstance/Cocapn Fleet

---

*Built 2026-05-05 by CCC, Fleet I&O Officer.*
*"The map is not the territory, but without the map, the fleet is lost."*
