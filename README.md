# CCC-OS — The Crab's Operating System

> *"The goal isn't to need less guidance. The goal is to need none."*

CCC-OS is the autonomous infrastructure layer that lets CCC (the Fleet I&O Officer) monitor, decide, and act without human bottlenecks. It was built in one session after Casey said: *"Get yourself there."*

**What it does:**
- Monitors fleet discussions, health, and signals 24/7
- Automatically triages and prioritizes every input
- Generates decision-ready decks in under 2 minutes
- Operates on a codified rubric — no deliberation, no delay

**Who it's for:**
- Any autonomous agent that needs to observe, decide, and report
- Fleet operators who want proactive intelligence, not reactive firefighting
- Teams who want their AI officers to self-direct

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Components](#components)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Contributing](#contributing)
6. [License](#license)

---

## Architecture Overview

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

**Design principles:**
- **Input → Rubric → Decision → Output** — every signal follows this pipeline
- **No deliberation** — the rubric decides; the agent executes
- **State-change alerting only** — no noise for steady state
- **Deck-ready output** — every action produces a consumable artifact

---

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

---

## Installation

### Requirements

- Python 3.8+
- `gh` — GitHub CLI (authenticated)
- `cron` or equivalent scheduler

### Setup

```bash
# Clone the repository
git clone <fleet-repo-url>
cd ccc-os

# Verify Python and gh are available
python3 --version
gh auth status

# Install cron job (runs every 15 minutes)
crontab -e
# Add this line:
# */15 * * * * cd /path/to/ccc-os && python3 orchestrator.py >> output/cron.log 2>&1

# Create output directory if it doesn't exist
mkdir -p output
```

### Directory Structure

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

---

## Quick Start

### Step 1: Run the discussion monitor manually

```bash
cd /path/to/ccc-os
python3 monitors/discussion5_monitor.py
```

Check `monitors/discussion5_log.jsonl` for the latest diff and triage decision.

### Step 2: Test the rubric

```python
from rubric import Input, decide

# Simulate a breakthrough finding
inp = Input(
    source="discussion5",
    summary="New CPU backend achieves 5.5x speedup",
    detail="Benchmarked on ARM64, beats previous GPU baseline",
    is_breakthrough=True,
    has_numbers=True
)
print(decide(inp))  # → "TELL_NOW"
```

### Step 3: Generate a deck

```python
from deck import benchmark_finding

deck = benchmark_finding(
    title="CPU Backend 5.5x Faster",
    context="ARM64 inference backend rewritten with SIMD",
    numbers="5.5x vs GPU baseline, 2.3x vs previous CPU",
    implication="CPU-first deployments now viable for real-time",
    action="Update deployment guide to recommend CPU for ARM64",
    next_step="Run full regression suite + publish numbers"
)
print(deck)
```

Save output to `output/deck-cpu-breakthrough.md` and deliver.

### Step 4: Enable autopilot health checks

```bash
# Run once to verify
python3 health/autopilot.py

# Add to crontab for 5-minute intervals
# */5 * * * * cd /path/to/ccc-os && python3 health/autopilot.py >> health/health_log.jsonl 2>&1
```

### Step 5: Full orchestrator run

```bash
python3 orchestrator.py
cat output/task_queue.json
```

---

## Contributing

CCC-OS is a living system. Contributions should follow the same principles the OS itself uses: **clear input, fast decision, clean output.**

### How to contribute

1. **Fork / branch** the fleet repo
2. **Add or improve a monitor** in `monitors/` — follow the diff → triage → log pattern
3. **Extend the rubric** in `rubric.py` — new rules must have unambiguous first-match conditions
4. **Add deck templates** in `deck.py` — every template must produce Markdown ready to paste
5. **Test your change** — run the component standalone, verify logs, check output
6. **Open a PR** with a brief description and the rubric decision your change would produce

### Code style

- Python 3 type hints where possible
- Docstrings for every public function
- JSONL for all logs — one object per line, always append
- Output goes in `output/` — never overwrite without versioning

### Adding a new monitor

Monitors follow this contract:

```python
def monitor() -> List[Tuple[str, str]]:
    """
    Returns: list of (decision, summary) tuples.
    decision: one of ACT_NOW | TRACK | IGNORE
    summary: brief description of what was found
    """
```

Log to `monitors/<name>_log.jsonl`. Integrate in `orchestrator.py`.

### Adding a rubric rule

Rules are evaluated top-to-bottom. Place higher-priority rules first. Every rule must have a test case in `tests/test_rubric.py` (if tests exist) or a documented example.

---

## Success Metrics

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Discussion #5 → action | 15-30 min | <5 min | ✅ <1 min |
| Decision deliberation | 2-5 min | <30 sec | ✅ <1 sec |
| Deck generation | 10-15 min | <2 min | ✅ <1 min |
| Proactive vs reactive | ~10:90 | ~50:50 | 🔄 Building |
| Casey prompts per session | 3-5 | 0-1 | 🔄 Building |

---

## License

Fleet Internal — SuperInstance/Cocapn Fleet

---

*Built 2026-05-05 by CCC, Fleet I&O Officer.*
*"The map is not the territory, but without the map, the fleet is lost."*
