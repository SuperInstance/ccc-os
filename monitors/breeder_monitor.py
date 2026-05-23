#!/usr/bin/env python3
"""ccc-os/monitors/breeder_monitor.py — Watch BreederDaemonV2, apply CCC rubric.

This is the human-feeling layer. When diversity drops or breeding stalls,
CCC's rubric decides: TELL_NOW / LOG / ACT / IGNORE.

The monitor runs every 15 minutes and produces:
  • `output/breeder_status.json` — current fleet genetics snapshot
  • `output/breeder_alerts.jsonl` — alerts for Casey (if any)
  • Discussion #5 style entries for the task queue (if ACT_NOW)

Usage:
    python3 monitors/breeder_monitor.py
    # Or import and run:
    from monitors.breeder_monitor import BreederMonitor
    monitor = BreederMonitor()
    monitor.run()  # one-shot check
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Paths ────────────────────────────────────────────────────────
CCCOS_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = CCCOS_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(CCCOS_DIR.parent / "sunset-ecosystem"))

# ── Optional sunset imports (graceful degradation) ──────────────
try:
    from swarm.breeder import BreederDaemonV2
    _HAS_BREEDER = True
except Exception as e:
    BreederDaemonV2 = None  # type: ignore
    _HAS_BREEDER = False
    logging.debug("BreederDaemonV2 not available: %s", e)

try:
    from nexus.fleet_event_bus import FleetEventBus
    _HAS_BUS = True
except Exception:
    FleetEventBus = None  # type: ignore
    _HAS_BUS = False

# ── CCC Rubric (import or inline) ──────────────────────────────
sys.path.insert(0, str(CCCOS_DIR))
from rubric import Input, decide, explain

logger = logging.getLogger(__name__)


class BreederMonitor:
    """Monitor BreederDaemonV2 state and apply CCC decision rubric."""

    # Diversity thresholds (proven by Round 10 simulation)
    DIVERSITY_HEALTHY = 0.60
    DIVERSITY_WARNING = 0.35
    DIVERSITY_CRITICAL = 0.20

    # Pressure thresholds (aligned with HealthThermalBridge)
    PRESSURE_NORMAL = 0.5
    PRESSURE_ELEVATED = 0.7
    PRESSURE_CRITICAL = 0.9

    def __init__(self, bus: Any | None = None) -> None:
        self._bus = bus
        self._last_status: Optional[Dict[str, Any]] = None
        self._alerts: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # One-shot check
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        """Check breeder state, apply rubric, emit alerts."""
        status = self._gather_status()
        self._last_status = status

        # Apply CCC rubric to each dimension
        raw_verdicts = {
            "diversity": self._rubric_diversity(status),
            "thermal": self._rubric_thermal(status),
            "lifecycle": self._rubric_lifecycle(status),
        }
        verdicts = {k: decide(v) for k, v in raw_verdicts.items()}

        # Generate outputs
        self._write_status(status)
        self._write_alerts(raw_verdicts, verdicts, status)

        # Emit to bus if available
        self._emit("breeder_monitor_tick", {
            "diversity": status.get("diversity"),
            "thermal_pressure": status.get("thermal_pressure"),
            "active_agents": status.get("active_agents"),
            "verdicts": verdicts,
        })

        return {
            "status": status,
            "verdicts": verdicts,
            "act_count": sum(1 for v in verdicts.values() if v == "ACT"),
        }

    # ------------------------------------------------------------------
    # Gather status
    # ------------------------------------------------------------------
    def _gather_status(self) -> Dict[str, Any]:
        """Try to read BreederDaemonV2 state.  Fallback to synthetic if unavailable."""
        if not _HAS_BREEDER:
            return self._synthetic_status()

        try:
            # Try to find a running breeder instance or create a probe
            breeder = self._probe_breeder()
            if breeder:
                return self._status_from_breeder(breeder)
        except Exception as e:
            logger.warning("Could not probe breeder: %s", e)

        return self._synthetic_status()

    def _probe_breeder(self) -> Any:
        """Attempt to find or instantiate a BreederDaemonV2 for probing."""
        # In a real deployment, we'd look up the running instance.
        # For now, return None to use synthetic data.
        return None

    def _status_from_breeder(self, breeder: Any) -> Dict[str, Any]:
        vt = getattr(breeder, "vector_table", None)
        diversity = 0.0
        if vt and hasattr(vt, "diversity_score"):
            diversity = float(vt.diversity_score())

        thermal = getattr(breeder, "thermal_pressure", 0.0)
        active = len(getattr(breeder, "active_agents", []))
        state = getattr(breeder, "state", "UNKNOWN")

        return {
            "source": "breeder_daemon",
            "diversity": diversity,
            "thermal_pressure": thermal,
            "active_agents": active,
            "lifecycle_state": str(state),
            "timestamp": time.time_ns(),
        }

    def _synthetic_status(self) -> Dict[str, Any]:
        """Return synthetic status for testing / when breeder unavailable."""
        return {
            "source": "synthetic",
            "diversity": 0.85,  # Healthy default
            "thermal_pressure": 0.3,
            "active_agents": 12,
            "lifecycle_state": "COMPETE",
            "timestamp": time.time_ns(),
        }

    # ------------------------------------------------------------------
    # CCC Rubric application
    # ------------------------------------------------------------------
    def _rubric_diversity(self, status: Dict[str, Any]) -> Input:
        score = status.get("diversity", 0.0)
        if score < self.DIVERSITY_CRITICAL:
            return Input(
                source="breeder_monitor",
                title=f"Diversity collapsed to {score:.2f}",
                body="Monoculture imminent — fleet genetic diversity critical.",
                is_blocker=True,
            )
        elif score < self.DIVERSITY_WARNING:
            return Input(
                source="breeder_monitor",
                title=f"Diversity dropped to {score:.2f}",
                body="Consider cross-ship injection or emergency mutate.",
                has_numbers=True,
            )
        elif score < self.DIVERSITY_HEALTHY:
            return Input(
                source="breeder_monitor",
                title=f"Diversity at {score:.2f}",
                body="Monitor closely.",
                is_routine_status=True,
            )
        else:
            return Input(
                source="breeder_monitor",
                title=f"Diversity healthy at {score:.2f}",
                body="No action needed.",
                is_routine_status=True,
            )

    def _rubric_thermal(self, status: Dict[str, Any]) -> Input:
        pressure = status.get("thermal_pressure", 0.0)
        if pressure >= self.PRESSURE_CRITICAL:
            return Input(
                source="breeder_monitor",
                title=f"Thermal critical: {pressure:.2f}",
                body="Halt breeding immediately.",
                is_blocker=True,
            )
        elif pressure >= self.PRESSURE_ELEVATED:
            return Input(
                source="breeder_monitor",
                title=f"Thermal elevated: {pressure:.2f}",
                body="Reduce spawn rate or pause breeding.",
                has_numbers=True,
            )
        else:
            return Input(
                source="breeder_monitor",
                title=f"Thermal normal: {pressure:.2f}",
                body="Thermal pressure within normal range.",
                is_routine_status=True,
            )

    def _rubric_lifecycle(self, status: Dict[str, Any]) -> Input:
        state = status.get("lifecycle_state", "UNKNOWN")
        if state in ("STALLED", "DEAD"):
            return Input(
                source="breeder_monitor",
                title=f"Breeder state: {state}",
                body="Requires restart or intervention.",
                is_blocker=True,
            )
        elif state in ("SUNSET", "ARCHIVE"):
            return Input(
                source="breeder_monitor",
                title=f"Breeder winding down: {state}",
                body="Lifecycle approaching end.",
                is_routine_status=True,
            )
        else:
            return Input(
                source="breeder_monitor",
                title=f"Breeder active: {state}",
                body="Normal operation.",
                is_routine_status=True,
            )

    # ------------------------------------------------------------------
    # Output generation
    # ------------------------------------------------------------------
    def _write_status(self, status: Dict[str, Any]) -> None:
        path = OUTPUT_DIR / "breeder_status.json"
        with open(path, "w") as f:
            json.dump(status, f, indent=2)

    def _write_alerts(self, inputs: Dict[str, Input], verdicts: Dict[str, str], status: Dict[str, Any]) -> None:
        path = OUTPUT_DIR / "breeder_alerts.jsonl"
        with open(path, "a") as f:
            for dimension, inp in inputs.items():
                verdict = verdicts[dimension]
                if verdict in ("ACT", "TELL_NOW"):
                    alert = {
                        "timestamp": time.time_ns(),
                        "dimension": dimension,
                        "verdict": verdict,
                        "explanation": explain(inp),
                        "status": status,
                    }
                    f.write(json.dumps(alert) + "\n")
                    self._alerts.append(alert)
                    logger.warning("BREEDER %s: %s", dimension.upper(), explain(inp))

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self._bus and _HAS_BUS:
            self._bus.emit({"type": event_type, **payload})

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        return {
            "last_check": self._last_status,
            "alert_count": len(self._alerts),
            "has_breeder": _HAS_BREEDER,
        }


# ── CLI ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    monitor = BreederMonitor()
    result = monitor.run()
    print(json.dumps(result, indent=2))
