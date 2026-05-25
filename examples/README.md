# Examples — CCC-OS Monitors

> *"Copy, paste, adapt."*

## Basic Monitor

```python
# examples/basic_monitor.py
from ccc_os import register_monitor

def check_heartbeat():
    """Minimal monitor — just returns OK."""
    return {"ok": True}

register_monitor("heartbeat", check_heartbeat, priority="P2")
```

## Multi-Metric Monitor

```python
# examples/multi_metric_monitor.py
from ccc_os import register_monitor
import random

def check_metrics():
    """Monitor with diversity, pressure, and count."""
    return {
        "ok": True,
        "diversity": random.uniform(0.5, 0.9),
        "pressure": random.uniform(0.1, 0.4),
        "agent_count": 42,
    }

register_monitor("metrics", check_metrics, priority="P1")
```

## Alerting Monitor

```python
# examples/alerting_monitor.py
from ccc_os import register_monitor

def check_diversity():
    """Monitor that raises alerts when diversity drops."""
    diversity = 0.28  # simulated low diversity
    alerts = []
    if diversity < 0.35:
        alerts.append({
            "action": "TELL_NOW",
            "reason": f"Diversity {diversity:.2f} below threshold 0.35",
        })
    return {
        "ok": len(alerts) == 0,
        "diversity": diversity,
        "alerts": alerts,
    }

register_monitor("diversity", check_diversity, priority="P0")
```

## Using MonitorRegistry Directly

```python
# examples/registry_demo.py
from ccc_os import MonitorRegistry

registry = MonitorRegistry()

registry.register("cpu", lambda: {"ok": True, "cpu": 0.45}, priority="P1")
registry.register("memory", lambda: {"ok": True, "memory": 0.62}, priority="P1")

status = registry.run_all()
print(f"Monitors: {status['monitors']}")
print(f"Alerts: {status['alerts']}")
print(f"Checked at: {status['checked_at']}")
```

## Running Examples

```bash
cd /path/to/ccc-os
python examples/basic_monitor.py
python -m ccc_os
```
