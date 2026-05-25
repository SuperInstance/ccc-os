# CCC-OS Plugin API

> *"Write a monitor in 10 minutes, not 10 hours."*

## Overview

CCC-OS supports pluggable monitors via the `register_monitor()` API. Any Python function that returns a status dict can be registered and will run alongside built-in monitors.

## Quick Example

```python
from ccc_os import register_monitor

def check_my_agent():
    return {
        "ok": True,
        "diversity": 0.75,
        "alerts": []
    }

register_monitor("my_agent", check_my_agent, priority="P1")
```

Then run:
```bash
python -m ccc_os
```

Your monitor appears in the fleet status table automatically.

## API Reference

### `register_monitor(name, check_fn, priority="P1")`

Register a monitor with the global registry.

**Parameters:**
- `name` (str): Human-readable monitor name
- `check_fn` (callable): Function returning a status dict
- `priority` (str): `P0` (critical), `P1` (standard), `P2` (informational)

**Returns:** None

### `MonitorRegistry`

For programmatic control, use `MonitorRegistry` directly:

```python
from ccc_os import MonitorRegistry

registry = MonitorRegistry()
registry.register("agent_a", check_a, priority="P0")
registry.register("agent_b", check_b, priority="P1")

status = registry.run_all()
print(status["monitors"])
```

### Status Dict Format

Your `check_fn` should return a dict with these optional keys:

```python
{
    "ok": True,                    # bool — overall health
    "diversity": 0.75,             # float — 0.0 to 1.0
    "pressure": 0.3,               # float — 0.0 to 1.0
    "alerts": [                    # list of alert dicts
        {
            "action": "TELL_NOW",
            "reason": "Diversity below threshold",
        }
    ]
}
```

## Versioning

**Current API version:** v1.0

- v1.0 (2026-05-25): Initial stable API
  - `register_monitor()` added
  - `MonitorRegistry` class added
  - Priority levels: P0, P1, P2

Breaking changes will bump the major version. Minor versions add features without breaking existing monitors.

## Error Handling

If your `check_fn` raises an exception, CCC-OS captures it and marks the monitor as failed:

```python
{
    "error": "Traceback...",
    "priority": "P1",
    "ok": False
}
```

Always handle expected errors inside your monitor to provide meaningful status.

## Examples

See `examples/` for complete working examples:
- `examples/basic_monitor.py` — minimal monitor
- `examples/multi_metric_monitor.py` — monitor with multiple metrics
- `examples/alerting_monitor.py` — monitor that triggers alerts

## Type Hints

```python
from typing import Callable, Dict, Any

def my_monitor() -> Dict[str, Any]:
    ...
```
