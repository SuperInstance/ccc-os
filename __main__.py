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
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

# Add parent to path for sunset-ecosystem imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sunset-ecosystem"))

from monitors.breeder_monitor import BreederMonitor


class MonitorRegistry:
    """Registry for pluggable fleet monitors.

    Usage:
        from ccc_os import register_monitor
        register_monitor("my_agent", my_check_function, priority="P1")

        # Or programmatically:
        registry = MonitorRegistry()
        registry.register("breeder", BreederMonitor().run, priority="P0")
        status = registry.run_all()
    """

    def __init__(self):
        self._monitors: Dict[str, tuple] = {}

    def register(
        self,
        name: str,
        check_fn: Callable[[], Dict[str, Any]],
        priority: str = "P1",
    ) -> None:
        """Register a monitor function.

        Args:
            name: Human-readable monitor name
            check_fn: Callable that returns a status dict
            priority: P0 (critical), P1 (standard), P2 (informational)
        """
        self._monitors[name] = (check_fn, priority)
        logging.info("Registered monitor: %s (priority=%s)", name, priority)

    def run_all(self) -> Dict[str, Any]:
        """Run all registered monitors and return combined status."""
        results = {}
        alerts = []
        for name, (fn, prio) in self._monitors.items():
            try:
                status = fn()
                results[name] = {"status": status, "priority": prio, "ok": True}
                # Extract alerts if present
                if isinstance(status, dict) and "alerts" in status:
                    for a in status["alerts"]:
                        a["source"] = name
                        alerts.append(a)
            except Exception as e:
                results[name] = {"error": str(e), "priority": prio, "ok": False}
                alerts.append({
                    "action": "TELL_NOW",
                    "reason": f"Monitor '{name}' failed: {e}",
                    "source": name,
                })

        return {
            "monitors": results,
            "alerts": alerts,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def list_monitors(self) -> List[str]:
        """Return list of registered monitor names."""
        return list(self._monitors.keys())


# Global singleton for convenient registration
_global_registry = MonitorRegistry()


def register_monitor(
    name: str,
    check_fn: Callable[[], Dict[str, Any]],
    priority: str = "P1",
) -> None:
    """Register a monitor with the global registry.

    Example:
        def check_my_agent():
            return {"ok": True, "diversity": 0.7}

        register_monitor("my_agent", check_my_agent, priority="P1")
    """
    _global_registry.register(name, check_fn, priority)


def run_all_monitors() -> Dict[str, Any]:
    """Run all registered monitors."""
    return _global_registry.run_all()


# ── CLI ─────────────────────────────────────────────────────────────


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
        if args.monitor == "all":
            # Use registry to run all registered monitors
            if not _global_registry.list_monitors():
                # Auto-register breeder as default
                _global_registry.register("breeder", BreederMonitor().run, priority="P0")
            status = _global_registry.run_all()
        elif args.monitor == "breeder":
            monitor = BreederMonitor()
            status = monitor.run()
        else:
            status = {"error": f"Unknown monitor: {args.monitor}"}
        
        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            # For registry output, print summary
            if "monitors" in status:
                lines = ["# CCC-OS Fleet Status", ""]
                for name, info in status["monitors"].items():
                    emoji = "🟢" if info.get("ok") else "🔴"
                    lines.append(f"| {emoji} {name} | {info.get('priority', 'P?')} | {'OK' if info.get('ok') else 'FAIL'} |")
                if status.get("alerts"):
                    lines.append("")
                    lines.append("## Alerts")
                    for a in status["alerts"]:
                        lines.append(f"- **{a.get('action', 'ACT')}**: {a.get('reason', 'No reason')}")
                print("\n".join(lines))
            else:
                print(_status_table(status))
        
        alerts = status.get("alerts", [])
        if not alerts and "monitors" in status:
            alerts = status.get("alerts", [])
        return len(alerts) == 0

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
