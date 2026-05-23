# CCC-OS Developer Guide

## Architecture

CCC-OS is an autonomous infrastructure layer with three core primitives:

1. **Observer** — Watches fleet discussions, health checks, and ZC feeds
2. **Decision Engine** — Applies the codified rubric to every input
3. **Actuator** — Generates reports, escalates blockers, logs routine items

## Quick Start

```python
from fleet.ccc_decision_rubric import Input, decide, explain

inp = Input(
    source="discussion5",
    title="CPU Breakthrough",
    body="5.5x speedup on JEPA grid",
    has_numbers=True,
    is_breakthrough=True,
)

decision = decide(inp)  # "TELL_NOW"
reason = explain(inp)   # "TELL_NOW — because: is a breakthrough, has benchmark numbers"
```

## Decision Rules

Rules are evaluated in order, first match wins:

| Priority | Condition | Action |
|----------|-----------|--------|
| P0 | Blocker on any path | `TELL_NOW` |
| P0 | Breakthrough >5x | `TELL_NOW` |
| P0 | Architecture affecting ≥2 repos | `TELL_NOW` |
| P1 | FM asks for Casey | `TELL_NOW` |
| P1 | Benchmark with numbers | `TELL_NOW` |
| P2 | Architecture, limited scope | `LOG` |
| P2 | Routine status | `IGNORE` |
| — | ZC feed | `LOG` |
| — | Health check, no change | `IGNORE` |
| — | Default | `LOG` |

## Adding a New Rule

Edit `fleet/ccc_decision_rubric.py`:

```python
# Example: escalate security findings immediately
(lambda i: "CVE" in i.body.upper(), "TELL_NOW"),
```

Add a test in `tests/test_ccc_decision_rubric.py`:

```python
def test_security_finding_tells_now(self):
    inp = Input("discussion5", "CVE found", "CVE-2024-1234")
    assert decide(inp) == "TELL_NOW"
```

## Testing

```bash
cd /root/.openclaw/workspace/sunset-ecosystem
pytest tests/test_ccc_decision_rubric.py -v
```

## Integration Points

| System | How CCC-OS Connects |
|--------|---------------------|
| Sunset Ecosystem | Reads `fleet/ccc_decision_rubric.py` for escalation logic |
| cocapn-health | Consumes `service_down` / `service_recovered` events |
| ZC Feed | Polls tiles, applies `zc_feed` rule |
| GitHub Discussions | Monitors Discussion #5, applies `discussion5` rules |

## Philosophy

The goal isn't to need less guidance. The goal is to need none.

Every input gets a decision in <1ms. No deliberation. No delay.
