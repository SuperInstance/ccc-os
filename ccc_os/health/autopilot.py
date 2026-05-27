"""Fleet Health Autopilot — Legacy interface, delegates to monitors.health.

This module is kept for backward compatibility.
New code should use ccc_os.monitors.health.HealthMonitor directly.
"""

from __future__ import annotations

import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_health_check(
    services: list[dict] | None = None,
    state_file: Path | None = None,
    log_file: Path | None = None,
) -> dict[str, Any]:
    """Run a health check on fleet services.

    Args:
        services: List of dicts with name, host, port, path keys
        state_file: Path to persist state between runs
        log_file: Path to write event log

    Returns:
        dict with services, up count, changes, etc.
    """
    if services is None:
        services = [
            {"name": "MUD", "host": "147.224.38.131", "port": 4042, "path": "/status"},
            {"name": "Arena", "host": "147.224.38.131", "port": 4044, "path": "/status"},
            {"name": "Grammar", "host": "147.224.38.131", "port": 4045, "path": "/status"},
        ]

    results = [_probe(**s) for s in services]
    up = sum(1 for r in results if r["status"] == "UP")

    return {"services": results, "up": up, "total": len(results)}


def _probe(name: str, host: str, port: int, path: str) -> dict:
    try:
        req = urllib.request.Request(f"http://{host}:{port}{path}", method="HEAD")
        req.add_header("User-Agent", "ccc-health/2.0")
        resp = urllib.request.urlopen(req, timeout=5)
        return {"name": name, "status": "UP", "code": resp.status}
    except Exception as e:
        return {"name": name, "status": "DOWN", "error": str(e)[:80]}


def main():
    """CLI entry point for health autopilot."""
    result = run_health_check()
    up = result["up"]
    total = result["total"]
    print(f"[{datetime.now(timezone.utc).isoformat()}] Health: {up}/{total} UP")
    for svc in result["services"]:
        icon = "🟢" if svc["status"] == "UP" else "🔴"
        print(f"  {icon} {svc['name']}")


if __name__ == "__main__":
    main()
