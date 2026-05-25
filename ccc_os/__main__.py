#!/usr/bin/env python3
"""ccc-os — CLI entry point for fleet monitoring.

Usage:
    ccc-os                              # Print fleet status table
    ccc-os --watch 900                  # Watch mode, 15 min interval
    ccc-os --monitor breeder            # Run specific monitor
    ccc-os --json                       # JSON output for CI pipelines
    ccc-os --serve                      # Start API server
    ccc-os --config /path/to/config.yaml # Use custom config
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import get_config
from .registry import MonitorRegistry, get_registry
from .rubric import Rubric
from .notifier import Notifier
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def _setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _auto_register_monitors(registry: MonitorRegistry):
    """Auto-register all available monitors."""
    from .monitors.breeder import BreederMonitor
    from .monitors.discussion5 import DiscussionMonitor
    from .monitors.zc import ZCMonitor
    from .monitors.health import HealthMonitor
    from .monitors.constraint import ConstraintMonitor

    config = get_config()

    monitors = [
        ("breeder", BreederMonitor, "P0"),
        ("discussion5", DiscussionMonitor, "P0"),
        ("zc", ZCMonitor, "P1"),
        ("health", HealthMonitor, "P1"),
        ("constraint", ConstraintMonitor, "P1"),
    ]

    for name, cls, priority in monitors:
        mon_config = config.monitor_config(name)
        if mon_config.get("enabled", True) and name not in registry.list_monitors():
            registry.register(name, cls(config).check, priority=priority)


def _status_table(status: dict) -> str:
    lines = [
        "# CCC-OS Fleet Status",
        "",
        f"**Checked at:** {status.get('checked_at', 'unknown')}",
        "",
        "| Monitor | Priority | Status |",
        "|---------|----------|--------|",
    ]

    for name, info in status.get("monitors", {}).items():
        emoji = "🟢" if info.get("ok") else "🔴"
        prio = info.get("priority", "P?")
        state = "OK" if info.get("ok") else "FAIL"
        lines.append(f"| {emoji} {name} | {prio} | {state} |")

    alerts = status.get("alerts", [])
    if alerts:
        lines.append("")
        lines.append("## Alerts")
        for a in alerts:
            lines.append(f"- **{a.get('action', 'ACT')}**: {a.get('reason', 'No reason')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="ccc-os",
        description="CCC fleet monitoring, decision, and action system",
    )
    parser.add_argument("--version", action="version", version=f"ccc-os {__version__}")
    parser.add_argument("--watch", type=int, help="Watch mode: recheck every N seconds")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--monitor",
        choices=["breeder", "discussion5", "zc", "health", "constraint", "all"],
        default="all",
        help="Which monitor to run",
    )
    parser.add_argument("--serve", action="store_true", help="Start API server")
    parser.add_argument("--config", type=str, help="Path to config YAML file")
    parser.add_argument("--log-level", type=str, default=None, help="Log level (DEBUG/INFO/WARNING)")
    args = parser.parse_args()

    # Load config
    config = get_config(args.config)
    log_level = args.log_level or config.log_level
    _setup_logging(log_level)

    # Get registry and auto-register monitors
    registry = get_registry()
    _auto_register_monitors(registry)

    # Handle --serve mode
    if args.serve:
        from .api import run_api_server
        logger.info("Starting API server on %s:%d", config.api_host, config.api_port)
        run_api_server(config.api_host, config.api_port, background=False)
        return

    def run_check():
        if args.monitor == "all":
            status = registry.run_all()
        else:
            result = registry.run_one(args.monitor)
            if result is None:
                print(f"Monitor '{args.monitor}' not registered")
                return False
            status = {
                "monitors": {args.monitor: result},
                "alerts": [],
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            print(_status_table(status))

        return len(status.get("alerts", [])) == 0

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
