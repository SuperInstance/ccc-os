"""Fleet Bridge — connects CCC-OS to the sunset-ecosystem FleetEventBus.

Gracefully degrades if sunset-ecosystem is not installed or FleetEventBus fails.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BUS_AVAILABLE = False
FleetEventBus = None


def _try_import_bus():
    global _BUS_AVAILABLE, FleetEventBus
    if _BUS_AVAILABLE:
        return True
    workspace = Path(__file__).resolve().parent.parent.parent
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


def is_bus_available() -> bool:
    """Check if FleetEventBus is available."""
    return _BUS_AVAILABLE


class FleetBridgeLogger:
    """Drop-in replacement for JSONL log_event() with optional bus emission.

    Writes to JSONL and emits to FleetEventBus when available.
    """

    def __init__(self, log_file: str | Path, source: str = "ccc-os"):
        self.log_file = Path(log_file)
        self.source = source
        self._bus = None
        if _BUS_AVAILABLE:
            try:
                self._bus = FleetEventBus()
            except Exception as exc:
                logger.warning("FleetEventBus instantiation failed: %s", exc)

    def log_event(self, event_dict: dict) -> None:
        """Write event to JSONL and emit to bus (best-effort)."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event_dict, default=str) + "\n")

        if self._bus is None:
            return

        event_type = event_dict.get("event_type") or event_dict.get("verdict") or "UNKNOWN"
        payload = {k: v for k, v in event_dict.items() if k not in ("event_type", "type")}

        try:
            self._bus.emit({"type": event_type, **payload}, source=self.source)
        except Exception as exc:
            logger.debug("Bus emit failed for %s: %s", event_type, exc)

    def emit(self, event_type: str, payload: dict) -> None:
        """Direct bus emit (no JSONL)."""
        if self._bus is None:
            return
        safe_payload = {k: v for k, v in payload.items() if k != "type"}
        try:
            self._bus.emit({"type": event_type, **safe_payload}, source=self.source)
        except Exception as exc:
            logger.debug("Bus emit failed for %s: %s", event_type, exc)
