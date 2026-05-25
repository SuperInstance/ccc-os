"""Base monitor abstract class for CCC-OS fleet monitors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MonitorResult:
    """Standard result from any monitor check."""
    name: str
    ok: bool
    status: dict[str, Any] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "ok": self.ok,
            "status": self.status,
            "alerts": self.alerts,
            "data": self.data,
        }
        if self.error:
            result["error"] = self.error
        return result


class BaseMonitor(ABC):
    """Abstract base class for all CCC-OS monitors.

    Subclasses must implement:
        - check() -> MonitorResult
        - last_state() -> dict
    """

    name: str = "base"
    priority: str = "P1"  # P0/P1/P2
    description: str = ""

    @abstractmethod
    def check(self) -> MonitorResult:
        """Run the monitor check and return results."""
        ...

    @abstractmethod
    def last_state(self) -> dict:
        """Return the last known state of this monitor."""
        ...

    def run(self) -> dict[str, Any]:
        """Run check and return dict (for registry compatibility)."""
        result = self.check()
        output = result.to_dict()
        return output
