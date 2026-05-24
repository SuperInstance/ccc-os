#!/usr/bin/env python3
"""ccc-os — CLI entry point for fleet monitoring.

Usage:
    python -m ccc_os                 # Print fleet status table
    python -m ccc_os --watch 900     # Watch mode, 15 min interval
    python -m ccc_os --monitor breeder  # Run specific monitor
    python -m ccc_os --json          # JSON output for CI pipelines
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent to path for sunset-ecosystem imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sunset-ecosystem"))

from monitors.breeder_monitor import BreederMonitor


def _status_table(status: dict) -> str:
    lines = [
        "# CCC-OS Fleet Status",
        "",
        f"**Checked at:** {status.get('checked_at', 'unknown')}",
        "",
        "| Metric | Value | Threshold | Status |",
        "|--------|-------|-----------|--------|",
    ]
    
    diversity = status.get("diversity", {})
    d_val = diversity.get("current", 0.0)
    d_thresh = diversity.get("threshold", 0.35)
    d_emoji = "🟢" if d_val > 0.6 else "🟡" if d_val > d_thresh else "🔴"
    lines.append(f"| Diversity | {d_val:.2f} | {d_thresh:.2f} | {d_emoji} |")
    
    pressure = status.get("pressure", {})
    p_val = pressure.get("current", 0.0)
    p_thresh = pressure.get("threshold", 0.7)
    p_emoji = "🟢" if p_val < 0.5 else "🟡" if p_val < p_thresh else "🔴"
    lines.append(f"| Pressure | {p_val:.2f} | {p_thresh:.2f} | {p_emoji} |")
    
    alerts = status.get("alerts", [])
    a_emoji = "🟢" if not alerts else "🔴"
    lines.append(f"| Alerts | {len(alerts)} | 0 | {a_emoji} |")
    
    if alerts:
        lines.append("")
        lines.append("## Alerts")
        for a in alerts:
            lines.append(f"- **{a.get('action', 'UNKNOWN')}**: {a.get('reason', 'No reason')}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(prog="ccc-os", description="CCC fleet monitoring")
    parser.add_argument("--watch", type=int, help="Watch mode: recheck every N seconds")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--monitor", choices=["breeder", "all"], default="all", help="Which monitor to run")
    args = parser.parse_args()

    def run_check():
        if args.monitor in ("breeder", "all"):
            monitor = BreederMonitor()
            status = monitor.run()
            
            if args.json:
                print(json.dumps(status, indent=2, default=str))
            else:
                print(_status_table(status))
            
            return len(status.get("alerts", [])) == 0
        return True

    if args.watch:
        try:
            while True:
                run_check()
                print(f"\n--- Rechecking in {args.watch}s ---\n")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            pass
    else:
        ok = run_check()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
