#!/usr/bin/env python3
"""
Fleet Bridge — connects CCC-OS monitors to the sunset-ecosystem FleetEventBus.

Gracefully degrades if sunset-ecosystem is not installed or FleetEventBus fails.
"""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ── graceful import of FleetEventBus ─────────────────────
_BUS_AVAILABLE = False
FleetEventBus = None


def _try_import_bus():
    global _BUS_AVAILABLE, FleetEventBus
    if _BUS_AVAILABLE:
        return True
    # Add sunset-ecosystem to path if it lives in the workspace
    workspace = Path(__file__).resolve().parent.parent
    se_path = workspace / "sunset-ecosystem"
    if str(se_path) not in sys.path:
        sys.path.insert(0, str(se_path))
    try:
        from nexus.fleet_event_bus import FleetEventBus as _Bus
        FleetEventBus = _Bus
        _BUS_AVAILABLE = True
        logger.debug("FleetEventBus imported successfully")
    except Exception as exc:
        logger.debug("FleetEventBus unavailable: %s", exc)
    return _BUS_AVAILABLE


_try_import_bus()


class FleetBridgeLogger:
    """
    Drop-in replacement for the JSONL log_event() functions in CCC-OS monitors.
    Writes to JSONL *and* emits to FleetEventBus when available.
    """

    def __init__(self, log_file, source="ccc-os"):
        self.log_file = Path(log_file)
        self.source = source
        self._bus = None
        if _BUS_AVAILABLE:
            try:
                self._bus = FleetEventBus()
            except Exception as exc:
                logger.warning("FleetEventBus instantiation failed: %s", exc)

    def log_event(self, event_dict):
        """
        Write event to JSONL and emit to bus (best-effort).

        event_dict may contain:
            - event_type: explicit bus event type (ACT_NOW, AGENT_SPAWN, AGENT_STATUS)
            - verdict:    fallback bus event type (ACT_NOW, TRACK, IGNORE)
        """
        # 1. Always write to JSONL (non-regression)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event_dict, default=str) + "\n")

        # 2. Best-effort bus emit
        if self._bus is None:
            return

        event_type = event_dict.get("event_type") or event_dict.get("verdict") or "UNKNOWN"
        # Strip internal/reserved keys from bus payload
        payload = {k: v for k, v in event_dict.items()
                   if k not in ("event_type", "type")}

        try:
            self._bus.emit({"type": event_type, **payload}, source=self.source)
        except Exception as exc:
            logger.debug("Bus emit failed for %s: %s", event_type, exc)

    def emit(self, event_type, payload):
        """
        Direct bus emit (no JSONL).  For events that only go to the bus.
        """
        if self._bus is None:
            return
        safe_payload = {k: v for k, v in payload.items() if k != "type"}
        try:
            self._bus.emit({"type": event_type, **safe_payload}, source=self.source)
        except Exception as exc:
            logger.debug("Bus emit failed for %s: %s", event_type, exc)
