"""Health Monitor — Probes fleet services and alerts on state changes.

Alerts ONLY on state changes (up→down or down→up). No noise for steady state.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone

from ..config import Config, get_config
from ..fleet_bridge import FleetBridgeLogger
from .base import BaseMonitor, MonitorResult

logger = logging.getLogger(__name__)


class HealthMonitor(BaseMonitor):
    """Probe fleet services and alert on state changes."""

    name = "health"
    priority = "P1"
    description = "Probes fleet services and alerts on state changes"

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._data_dir = self.config.data_dir / "health"
        self._state_file = self._data_dir / "last_health.json"
        self._bridge = FleetBridgeLogger(
            self._data_dir / "health_log.jsonl",
            source="ccc-os/health",
        )

    def check(self) -> MonitorResult:
        """Run health check on all configured services."""
        services = self.config.health_services()
        current_results = [self._probe(**s) for s in services]
        up = sum(1 for r in current_results if r["status"] == "UP")

        last = self._load_last()
        last_map = {s["name"]: s["status"] for s in last.get("services", [])}

        alerts = []
        changes = []
        for svc in current_results:
            prev = last_map.get(svc["name"])
            if prev and prev != svc["status"]:
                change = {
                    "name": svc["name"],
                    "from": prev,
                    "to": svc["status"],
                    "details": svc.get("error", ""),
                }
                changes.append(change)
                if svc["status"] == "DOWN":
                    alerts.append({
                        "action": "TELL_NOW",
                        "reason": f"{svc['name']}: {prev} → {svc['status']} ({svc.get('error', '')})",
                        "source": "health",
                    })

        if changes:
            self._bridge.log_event({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "state_change",
                "changes": changes,
                "up": up,
                "total": len(current_results),
            })

        current = {"services": current_results, "up": up, "total": len(current_results)}
        self._save_state(current)

        return MonitorResult(
            name=self.name,
            ok=len(alerts) == 0,
            status=current,
            alerts=alerts,
            data={"changes": changes},
        )

    def last_state(self) -> dict:
        return self._load_last()

    def _probe(self, name: str, host: str, port: int, path: str) -> dict:
        try:
            req = urllib.request.Request(
                f"http://{host}:{port}{path}", method="HEAD"
            )
            req.add_header("User-Agent", "ccc-health/2.0")
            resp = urllib.request.urlopen(req, timeout=5)
            return {"name": name, "status": "UP", "code": resp.status}
        except Exception as e:
            return {"name": name, "status": "DOWN", "error": str(e)[:80]}

    def _load_last(self) -> dict:
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"services": []}

    def _save_state(self, state: dict) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)
