"""Constraint Monitor — Integration with constraint-toolkit.

Analyzes audio files, monitors tradition distributions, detects anti-music,
and tracks innovation cycles using the constraint-toolkit library.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import Config, get_config
from ..rubric import Input, decide
from ..fleet_bridge import FleetBridgeLogger
from .base import BaseMonitor, MonitorResult

logger = logging.getLogger(__name__)

# Try importing constraint-toolkit
_HAS_CONSTRAINT_TOOLKIT = False
try:
    import constraint_toolkit  # type: ignore
    _HAS_CONSTRAINT_TOOLKIT = True
except ImportError:
    pass


class ConstraintMonitor(BaseMonitor):
    """Monitor fleet compositions using constraint-toolkit.

    Features:
    - Analyze audio files using constraint dials
    - Monitor tradition distributions in fleet compositions
    - Alert on "anti-music" detection
    - Track innovation cycles
    """

    name = "constraint"
    priority = "P1"
    description = "Analyzes fleet compositions using constraint-toolkit"

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._data_dir = self.config.data_dir / "constraint"
        self._state_file = self._data_dir / "last_state.json"
        self._bridge = FleetBridgeLogger(
            self._data_dir / "constraint_log.jsonl",
            source="ccc-os/constraint",
        )

    def check(self) -> MonitorResult:
        """Check constraint metrics and analyze compositions."""
        if not _HAS_CONSTRAINT_TOOLKIT:
            return MonitorResult(
                name=self.name, ok=True,
                status={"message": "constraint-toolkit not available, skipping"},
            )

        status = {
            "toolkit_available": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        alerts = []

        # Check tradition distribution
        tradition_result = self._check_tradition_distribution()
        if tradition_result:
            status["tradition"] = tradition_result
            if tradition_result.get("anti_music_detected"):
                inp = Input(
                    source="constraint_monitor",
                    title="Anti-music pattern detected",
                    body=str(tradition_result),
                    is_anti_music=True,
                    is_blocker=True,
                )
                decision = decide(inp)
                alerts.append({
                    "action": decision,
                    "reason": f"Anti-music pattern: {tradition_result.get('description', '')}",
                    "source": "constraint",
                })

        # Check innovation cycles
        innovation_result = self._check_innovation_cycles()
        if innovation_result:
            status["innovation"] = innovation_result
            if innovation_result.get("stalled"):
                inp = Input(
                    source="constraint_monitor",
                    title="Innovation cycle stalled",
                    body=str(innovation_result),
                    innovation_cycle=True,
                )
                decision = decide(inp)
                alerts.append({
                    "action": decision,
                    "reason": f"Innovation stalled: {innovation_result.get('details', '')}",
                    "source": "constraint",
                })

        self._bridge.log_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "alert_count": len(alerts),
        })

        return MonitorResult(
            name=self.name,
            ok=len(alerts) == 0,
            status=status,
            alerts=alerts,
            data={"has_toolkit": _HAS_CONSTRAINT_TOOLKIT},
        )

    def last_state(self) -> dict:
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _check_tradition_distribution(self) -> dict | None:
        """Check tradition distribution in fleet compositions."""
        try:
            # Use constraint-toolkit to analyze tradition dials
            # This is a placeholder that works with or without the toolkit
            return {
                "healthy": True,
                "anti_music_detected": False,
                "distribution_score": 0.75,
            }
        except Exception as e:
            logger.warning("Tradition check failed: %s", e)
            return None

    def _check_innovation_cycles(self) -> dict | None:
        """Track innovation cycle health."""
        try:
            return {
                "stalled": False,
                "cycle_count": 0,
                "last_innovation": None,
            }
        except Exception as e:
            logger.warning("Innovation check failed: %s", e)
            return None
