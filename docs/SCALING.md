# CCC-OS Scaling Guide

> *"One node is a prototype. Twelve nodes is a fleet."*

## Single-Node Setup

The default CCC-OS configuration runs on a single machine:

```bash
python -m ccc_os --watch 900
```

This monitors the local sunset-ecosystem instance and reports every 15 minutes.

## Multi-Node Setup

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Node 1     │────▶│  Node 2     │────▶│  Node 3     │
│  ccc-os     │     │  ccc-os     │     │  ccc-os     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                    ┌─────────────┐
                    │  Aggregator │
                    │  (optional) │
                    └─────────────┘
```

Each node runs CCC-OS independently. The `fleet_bridge.py` module handles cross-node communication via JSONL files and an optional message bus.

### Node Discovery

Nodes discover each other through the fleet bridge:

1. Each node writes its status to a shared `fleet_bridge.jsonl`
2. The bridge broadcasts updates to all subscribers
3. CCC-OS on each node reads the shared state

**Configuration:** Set `FLEET_BRIDGE_PATH` env var to point to a shared filesystem or network mount:

```bash
export FLEET_BRIDGE_PATH=/shared/fleet_bridge.jsonl
python -m ccc_os
```

### Scaling Checklist

| Nodes | Action | Status |
|-------|--------|--------|
| 1 | Single-node, local monitoring | ✅ Default |
| 2-5 | Shared `fleet_bridge.jsonl` | ✅ Supported |
| 6-12 | Dedicated aggregator node | ✅ Recommended |
| 12+ | Sharded monitoring + mesh gossip | 🚧 Planned |

### Aggregator Node

For 6+ nodes, run a dedicated aggregator:

```python
# aggregator.py
from ccc_os import MonitorRegistry
import json

registry = MonitorRegistry()
# Register remote monitors that poll each node
for node_id in range(1, 13):
    registry.register(f"node_{node_id}", make_remote_check(node_id), priority="P0")

status = registry.run_all()
print(json.dumps(status, indent=2))
```

### Performance Limits

| Metric | Single Node | 12 Nodes | Notes |
|--------|-------------|----------|-------|
| Checks/sec | ~50 | ~600 | Limited by Python GIL |
| Memory | ~50 MB | ~100 MB | Per CCC-OS instance |
| Disk (jsonl) | ~1 MB/day | ~12 MB/day | Rotated weekly |
| Network | N/A | ~1 KB/sec | Per node, bridge traffic |

## Horizontal Scaling

For fleets beyond 12 nodes, we recommend:

1. **Sharded monitoring**: Each CCC-OS instance monitors a subset of nodes
2. **Mesh gossip**: Use `sunset-ecosystem` mesh gossip for decentralized state sharing
3. **Tiered aggregation**: Leaf nodes → regional aggregators → central dashboard

## Configuration

All scaling parameters are controlled via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLEET_BRIDGE_PATH` | `./fleet_bridge.jsonl` | Shared state file |
| `CCC_OS_WATCH_INTERVAL` | `900` | Watch mode interval (seconds) |
| `CCC_OS_MAX_ALERTS` | `100` | Alert buffer size |
| `CCC_OS_LOG_LEVEL` | `INFO` | Logging verbosity |

## Troubleshooting at Scale

### Stale Bridge Data
**Symptom:** Nodes show outdated status.
**Fix:** Check filesystem write latency. Consider using Redis or NATS instead of shared file.

### Alert Flooding
**Symptom:** Too many alerts from 12 nodes.
**Fix:** Use the aggregator to deduplicate. Set `CCC_OS_MAX_ALERTS` lower on leaf nodes.

### Memory Growth
**Symptom:** CCC-OS memory grows over days.
**Fix:** Restart periodically (via systemd) or reduce jsonl retention.
