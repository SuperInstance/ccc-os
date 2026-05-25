# CCC-OS Runbook

> *"When something breaks at 3 AM, this is the first page you open."*

## Quick Diagnostics

### Check Fleet Status
```bash
python -m ccc_os
```

### Watch Mode (continuous monitoring)
```bash
python -m ccc_os --watch 300
```

### Check Specific Monitor
```bash
python -m ccc_os --monitor breeder
```

### JSON Output (for CI pipelines)
```bash
python -m ccc_os --json
```

## Common Issues

### Monitor Not Found
**Symptom:** `Unknown monitor: 'xyz'`
**Fix:** Ensure the monitor module is in `monitors/` and imported in `__main__.py`.

### Registry Empty
**Symptom:** No monitors registered on first run.
**Fix:** The breeder monitor auto-registers. For custom monitors, call `register_monitor()` before `run_all()`.

### High Alert Count
**Symptom:** Red alerts in status table.
**Check:**
1. Is the sunset-ecosystem repo running? `ps aux | grep sunset`
2. Is the fleet bridge connected? Check `fleet_bridge.jsonl`
3. Are monitors throwing exceptions? Check logs.

### Performance Degradation
**Symptom:** Watch mode feels slow.
**Fix:** Reduce `--watch` interval or run specific monitors instead of `--monitor all`.

## Escalation

| Severity | Action | Contact |
|----------|--------|---------|
| P0 (fleet down) | Page on-call + restart orchestrator | #fleet-ops |
| P1 (degraded) | Open incident ticket | #harbor |
| P2 (warning) | Log and monitor | Automated |

## Metrics Endpoint

CCC-OS exposes fleet status as JSON at the CLI level. For Prometheus-style scraping, pipe `--json` output to your metrics collector.

```bash
# Cron job for metrics export
*/5 * * * * cd /opt/ccc-os && python -m ccc_os --json > /var/lib/prometheus/ccc-os.json
```

## Recovery Procedures

### Restart After Crash
```bash
cd /opt/ccc-os
python -m ccc_os --monitor all
```

### Clear Stuck Alerts
Alerts are ephemeral — they clear on next successful check. If stuck, restart the monitor.

## Contact

- **Fleet Ops:** `#fleet-ops` on Matrix
- **CCC-OS Maintainer:** Open a GitHub issue
