"""Breeder Monitor — Watch fleet genetic diversity, thermal pressure, and lifecycle.

Applies CCC rubric to breeder state and generates alerts.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from ..config import Config, get_config
from ..fleet_bridge import FleetBridgeLogger
from ..rubric import Input, decide, explain
from .base import BaseMonitor, MonitorResult

logger = logging.getLogger(__name__)

# Optional sunset-ecosystem imports
_HAS_BREEDER = False
BreederDaemonV2 = None
try:
    import sys
    se_path = Path(__file__).resolve().parent.parent.parent.parent / "sunset-ecosystem"
    if str(se_path) not in sys.path:
        sys.path.insert(0, str(se_path))
    from swarm.breeder import BreederDaemonV2 as _BD
    BreederDaemonV2 = _BD
    _HAS_BREEDER = True
except Exception:
    pass


class BreederMonitor(BaseMonitor):
    """Monitor BreederDaemonV2 state and apply CCC decision rubric."""

    name = "breeder"
    priority = "P0"
    description = "Watches fleet genetic diversity, thermal pressure, and lifecycle state"

    DIVERSITY_HEALTHY = 0.60
    DIVERSITY_WARNING = 0.35
    DIVERSITY_CRITICAL = 0.20
    PRESSURE_NORMAL = 0.5
    PRESSURE_ELEVATED = 0.7
    PRESSURE_CRITICAL = 0.9

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._last_status: dict[str, Any] | None = None
        self._alerts: list[dict[str, Any]] = []
        output_dir = self.config.output_dir
        self._bridge = FleetBridgeLogger(
            output_dir / "breeder_alerts.jsonl", source="ccc-os/breeder"
        )

    def check(self) -> MonitorResult:
        """Check breeder state, apply rubric, emit alerts."""
        status = self._gather_status()
        self._last_status = status

        raw_verdicts = {
            "diversity": self._rubric_diversity(status),
            "thermal": self._rubric_thermal(status),
            "lifecycle": self._rubric_lifecycle(status),
        }
        verdicts = {k: decide(v) for k, v in raw_verdicts.items()}

        # Write outputs
        self._write_status(status)

        alerts = []
        for dimension, inp in raw_verdicts.items():
            verdict = verdicts[dimension]
            if verdict in ("ACT", "TELL_NOW"):
                alert = {
                    "action": verdict,
                    "dimension": dimension,
                    "explanation": explain(inp),
                    "status": status,
                }
                alerts.append(alert)
                self._alerts.append(alert)
                self._bridge.log_event(alert)
                logger.warning("BREEDER %s: %s", dimension.upper(), explain(inp))

        act_count = sum(1 for v in verdicts.values() if v in ("ACT", "TELL_NOW"))

        return MonitorResult(
            name=self.name,
            ok=act_count == 0,
            status=status,
            alerts=alerts,
            data={"verdicts": verdicts, "act_count": act_count},
        )

    def last_state(self) -> dict:
        return self._last_status or {}

    def _gather_status(self) -> dict[str, Any]:
        if _HAS_BREEDER:
            try:
                breeder = self._probe_breeder()
                if breeder:
                    return self._status_from_breeder(breeder)
            except Exception as e:
                logger.warning("Could not probe breeder: %s", e)
        return self._synthetic_status()

    def _probe_breeder(self):
        return None

    def _status_from_breeder(self, breeder) -> dict:
        vt = getattr(breeder, "vector_table", None)
        diversity = 0.0
        if vt and hasattr(vt, "diversity_score"):
            diversity = float(vt.diversity_score())
        return {
            "source": "breeder_daemon",
            "diversity": diversity,
            "thermal_pressure": getattr(breeder, "thermal_pressure", 0.0),
            "active_agents": len(getattr(breeder, "active_agents", [])),
            "lifecycle_state": str(getattr(breeder, "state", "UNKNOWN")),
            "timestamp": time.time_ns(),
        }

    def _synthetic_status(self) -> dict:
        return {
            "source": "synthetic",
            "diversity": 0.85,
            "thermal_pressure": 0.3,
            "active_agents": 12,
            "lifecycle_state": "COMPETE",
            "timestamp": time.time_ns(),
        }

    def _rubric_diversity(self, status: dict) -> Input:
        score = status.get("diversity", 0.0)
        if score < self.DIVERSITY_CRITICAL:
            return Input("breeder_monitor", f"Diversity collapsed to {score:.2f}",
                         "Monoculture imminent", is_blocker=True)
        elif score < self.DIVERSITY_WARNING:
            return Input("breeder_monitor", f"Diversity dropped to {score:.2f}",
                         "Consider cross-ship injection", has_numbers=True)
        elif score < self.DIVERSITY_HEALTHY:
            return Input("breeder_monitor", f"Diversity at {score:.2f}",
                         "Monitor closely", is_routine_status=True)
        else:
            return Input("breeder_monitor", f"Diversity healthy at {score:.2f}",
                         "No action needed", is_routine_status=True)

    def _rubric_thermal(self, status: dict) -> Input:
        pressure = status.get("thermal_pressure", 0.0)
        if pressure >= self.PRESSURE_CRITICAL:
            return Input("breeder_monitor", f"Thermal critical: {pressure:.2f}",
                         "Halt breeding immediately", is_blocker=True)
        elif pressure >= self.PRESSURE_ELEVATED:
            return Input("breeder_monitor", f"Thermal elevated: {pressure:.2f}",
                         "Reduce spawn rate", has_numbers=True)
        else:
            return Input("breeder_monitor", f"Thermal normal: {pressure:.2f}",
                         "Normal range", is_routine_status=True)

    def _rubric_lifecycle(self, status: dict) -> Input:
        state = status.get("lifecycle_state", "UNKNOWN")
        if state in ("STALLED", "DEAD"):
            return Input("breeder_monitor", f"Breeder state: {state}",
                         "Requires intervention", is_blocker=True)
        elif state in ("SUNSET", "ARCHIVE"):
            return Input("breeder_monitor", f"Breeder winding down: {state}",
                         "Lifecycle approaching end", is_routine_status=True)
        else:
            return Input("breeder_monitor", f"Breeder active: {state}",
                         "Normal operation", is_routine_status=True)

    def _write_status(self, status: dict) -> None:
        path = self.config.output_dir / "breeder_status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(status, f, indent=2)
