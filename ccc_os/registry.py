"""CCC-OS Registry — Pluggable monitor registry.

Manages registration and execution of fleet monitors.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class MonitorRegistry:
    """Registry for pluggable fleet monitors.

    Usage:
        registry = MonitorRegistry()
        registry.register("breeder", my_check_fn, priority="P0")
        status = registry.run_all()
    """

    def __init__(self):
        self._monitors: Dict[str, tuple[Callable, str]] = {}

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
        logger.info("Registered monitor: %s (priority=%s)", name, priority)

    def unregister(self, name: str) -> bool:
        """Remove a monitor by name. Returns True if it existed."""
        if name in self._monitors:
            del self._monitors[name]
            return True
        return False

    def run_all(self) -> Dict[str, Any]:
        """Run all registered monitors and return combined status."""
        results = {}
        alerts = []
        for name, (fn, prio) in self._monitors.items():
            try:
                status = fn()
                results[name] = {"status": status, "priority": prio, "ok": True}
                if isinstance(status, dict) and "alerts" in status:
                    for a in status["alerts"]:
                        a["source"] = name
                        alerts.append(a)
            except Exception as e:
                logger.exception("Monitor '%s' failed", name)
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

    def run_one(self, name: str) -> Dict[str, Any] | None:
        """Run a single monitor by name. Returns None if not found."""
        if name not in self._monitors:
            return None
        fn, prio = self._monitors[name]
        try:
            status = fn()
            return {"status": status, "priority": prio, "ok": True}
        except Exception as e:
            return {"error": str(e), "priority": prio, "ok": False}

    def list_monitors(self) -> List[str]:
        """Return list of registered monitor names."""
        return list(self._monitors.keys())

    def get_monitor_info(self, name: str) -> Dict[str, str] | None:
        """Get info about a registered monitor."""
        if name not in self._monitors:
            return None
        _, prio = self._monitors[name]
        return {"name": name, "priority": prio}


# Global singleton
_global_registry = MonitorRegistry()


def register_monitor(
    name: str,
    check_fn: Callable[[], Dict[str, Any]],
    priority: str = "P1",
) -> None:
    """Register a monitor with the global registry."""
    _global_registry.register(name, check_fn, priority)


def run_all_monitors() -> Dict[str, Any]:
    """Run all globally registered monitors."""
    return _global_registry.run_all()


def get_registry() -> MonitorRegistry:
    """Get the global registry instance."""
    return _global_registry
