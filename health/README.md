# Fleet Health Autopilot

Probes 8 fleet services every 5 minutes. Alerts **only** on state changes (up→down or down→up). No noise for steady state.

## Services Monitored

| Service | Host | Port | Path | Why |
|---------|------|------|------|-----|
| MUD | 147.224.38.131 | 4042 | /status | Primary fleet interface |
| Arena | 147.224.38.131 | 4044 | /status | Combat testing |
| Grammar | 147.224.38.131 | 4045 | /status | Rule engine |
| PLATO Gate | 147.224.38.131 | 8847 | /status | Tile ingestion |
| PLATO Shell | 147.224.38.131 | 8848 | / | Shell bridge |
| Rate-Attention | 147.224.38.131 | 4056 | /status | Stream monitoring |
| Skill Forge | 147.224.38.131 | 4057 | /status | Training pipeline |
| Matrix Bridge | 147.224.38.131 | 6168 | /status | Fleet messaging |

## How It Works

1. **HEAD request** to each service's status endpoint
2. **Compare** against `health/last_health.json`
3. **Alert** only if status changed from previous check
4. **Log** state changes to `health/health_log.jsonl`

## Output Format

### Console (normal run)
```
No changes. 6/8 UP.
```

### State Change
```
⚠️ STATE CHANGES: 2
🔴 PLATO Gate: UP → DOWN
   Connection refused
🟢 Matrix Bridge: DOWN → UP
```

### Log Entry
```json
{
  "timestamp": "2026-05-04T02:43:36Z",
  "type": "state_change",
  "changes": [
    {"name": "PLATO Gate", "from": "UP", "to": "DOWN", "details": "Connection refused"}
  ],
  "up": 6,
  "total": 8
}
```

## Adding New Services

Edit the `SERVICES` list in `health/autopilot.py`:

```python
SERVICES = [
    ("MUD", "147.224.38.131", 4042, "/status"),
    ("Your Service", "host", port, "/status"),
    # ...
]
```

## Architecture Note

The health checker uses lightweight HEAD requests (not full GETs) to minimize load on services. A 5-second timeout prevents hangs. The state-file approach means we only alert when something actually changes — no spam.

## Usage

```bash
python3 health/autopilot.py
```

Or via orchestrator:
```bash
python3 orchestrator.py
```

---

*Part of CCC-OS. See [../README.md](../README.md) for overview.*
