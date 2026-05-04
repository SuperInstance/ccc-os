# CCC-OS Architecture

## Design Philosophy

CCC-OS exists because of one insight: **the bottleneck in autonomous systems is not the acting — it's the deciding.**

Every AI assistant can execute. The hard part is knowing:
- What should I pay attention to?
- Should I tell the human now or log it?
- Is this my job or someone else's?

CCC-OS solves this with three principles:

### 1. Monitor, Don't Poll

The human should never ask "what's new?" The system should already know.

- Discussion #5: auto-poll every 15 min
- Fleet health: auto-probe every 5 min
- ZC feeds: auto-ingest every 15 min (planned)

### 2. Decide With Rules, Not Judgment

Deliberation is expensive. Rules are cheap.

The rubric is a list of predicates evaluated in order. First match wins. No "it depends." No "let me think about it." The decision is made in milliseconds and logged for review.

**Key insight:** A wrong rule can be fixed. Ambiguity can't.

### 3. Generate, Don't Compose

Every output should be template-driven. A deck is not "written" — it's filled in.

- Benchmark deck: context, numbers, implication, action, next
- Architecture deck: problem, options, recommendation, risk, timeline
- Fleet status: up/down, tiles, blockers

**Target time:** <2 minutes from raw data to Casey-ready deck.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                            │
├─────────────────┬─────────────────┬───────────────────────────┤
│  Discussion #5  │  Fleet Health   │  ZC Feeds (planned)       │
│  GitHub GraphQL │  HTTP HEAD      │  File system tail         │
│  Every 15 min   │  Every 5 min    │  Every 15 min             │
└─────────────────┴─────────────────┴───────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DECISION LAYER                             │
│                     (rubric.py)                               │
├─────────────────────────────────────────────────────────────┤
│  TELL_NOW  →  Generate deck → Deliver to Casey              │
│  LOG       →  Write to backlog → Queue for later            │
│  ACT       →  Execute directly (no human needed)              │
│  IGNORE    →  Drop silently                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                               │
├─────────────────┬─────────────────┬───────────────────────────┤
│  Decks (.md)    │  Task Queue     │  Bottles (to Oracle1)     │
│  Human-readable │  JSON priority  │  Markdown summaries       │
│  ≤5 slides      │  Auto-generated │  Fleet coordination       │
└─────────────────┴─────────────────┴───────────────────────────┘
```

## State Management

CCC-OS uses a simple state model:

- **State files** (JSON): Last known good state. Used for diffing.
  - `monitors/discussion5_last_state.json`
  - `health/last_health.json`

- **Log files** (JSONL): Append-only event stream. Used for auditing and queue generation.
  - `monitors/discussion5_log.jsonl`
  - `health/health_log.jsonl`

- **Output files** (JSON + Markdown): Generated artifacts.
  - `output/task_queue.json`
  - `output/deck-*.md`

**Principle:** State is for the machine. Logs are for the human. Output is for action.

## The Rubric

```python
RULES = [
    # P0: Blockers on any publishing/deploy path
    (lambda i: i.is_blocker, "TELL_NOW"),
    # P0: Breakthrough >5x improvement
    (lambda i: i.is_breakthrough, "TELL_NOW"),
    # P0: Architecture change affecting ≥2 repos
    (lambda i: i.is_architecture and i.affects_repos >= 2, "TELL_NOW"),
    # P1: FM explicitly asking for Casey
    (lambda i: i.asks_for_casey, "TELL_NOW"),
    # P1: New benchmark with numbers
    (lambda i: i.has_numbers and i.source == "discussion5", "TELL_NOW"),
    # P2: Architecture change, limited scope
    (lambda i: i.is_architecture, "LOG"),
    # P2: Routine status from known agents
    (lambda i: i.is_routine_status, "IGNORE"),
    # P2: Technical question FM→Oracle1
    (lambda i: i.source == "discussion5" and "oracle1" in i.body.lower() and "?" in i.body, "LOG"),
    # Default: Everything else
    (lambda _: True, "LOG"),
]
```

**Priority levels:**
- **P0** — Interrupt Casey immediately. Blockers, breakthroughs, architecture.
- **P1** — Generate deck, queue for delivery. Benchmarks, explicit requests.
- **P2** — Log silently. Routine updates, technical Q&A.

## Deck Templates

### Benchmark Finding
```
Slide 1: Context — What was tested?
Slide 2: The Numbers — Head-to-head results
Slide 3: What This Means — Strategic implication
Slide 4: What We Should Do — Action items
Slide 5: Next — Specific next steps with owners
```

### Architecture Decision
```
Slide 1: The Problem — What are we solving?
Slide 2: Options — What could we do?
Slide 3: Recommendation — What should we do?
Slide 4: Risk — What could go wrong?
Slide 5: Timeline — When do we do it?
```

### Fleet Status
```
Slide 1: Services — Up/down counts
Slide 2: PLATO — New tiles this cycle
Slide 3: Blockers — Anything stuck?
```

### Research Summary
```
Slide 1: What We Learned — Key findings
Slide 2: Why It Matters — Fleet relevance
Slide 3: What To Do — Action items
```

## Extension Points

### Adding a New Monitor

1. Create `monitors/your_monitor.py`
2. Implement `fetch()` → returns structured data
3. Implement `triage()` → returns ACT_NOW / TRACK / IGNORE
4. Add to `orchestrator.py` in the `main()` function
5. Log events to `monitors/your_monitor_log.jsonl`

### Adding a New Deck Template

1. Add function to `deck.py`
2. Define `Slide` sequence
3. Document in `output/README.md`

### Adding a New Rubric Rule

1. Add predicate to `RULES` list in `rubric.py`
2. Place in correct priority order
3. Update `explain()` if needed

## Failure Modes

| Failure | Mitigation |
|---------|-----------|
| `gh` CLI not authenticated | Fails silently, logs error, retries next cycle |
| Network unreachable | All probes return DOWN, delta detected if state changes |
| False positive triage | Review `discussion5_log.jsonl`, adjust signals |
| Missed ACT_NOW | Escalate if item sits in queue >30 min without action |
| State file corruption | Delete `.json` file, next run fetches fresh |

## Future Work

- **ZC Feed Monitor** — Auto-ingest `data/zeroclaw/logs/`, summarize, queue
- **Auto-Delivery** — When TELL_NOW, auto-post to Telegram + Discussion #5
- **Bottle Generator** — Auto-create Markdown bottles for Oracle1 queue
- **MUD Scout** — Spawn explorer agent every 6 hours, report changes
- **Landing Page Auto-Update** — Generate domain copy from latest tiles

## Principles for Contributors

1. **No deliberation** — If a decision takes more than 30 seconds, it should be a rule
2. **Append-only logs** — Never delete log entries. State changes, not state overwrites.
3. **Template everything** — Every output format should be fill-in-the-blank
4. **Alert on delta** — Only notify humans when something changes
5. **Human review, machine execution** — The rubric decides. The human can override. The machine does the work.

---

*CCC-OS v1.0 | Fleet I&O Infrastructure*
*"The map is not the territory, but without the map, the fleet is lost."*
