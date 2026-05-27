"""ComputeNode — Represents a node in the CCC-OS compute fleet.

Tracks capacity, health, workload, and labels for placement decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeStatus(Enum):
    """Node health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    DRAINING = "draining"
    OFFLINE = "offline"


@dataclass
class ComputeNode:
    """A single compute node in the fleet.

    Attributes:
        node_id: Unique identifier.
        labels: Tags for affinity/anti-affinity (e.g., {"gpu", "us-west"}).
        cpu_total: Total CPU cores available.
        memory_total: Total memory in GB.
        gpu_total: Total GPUs available.
        cost_per_hour: Cost to use this node per hour.
        status: Current health status.
    """
    node_id: str
    labels: set[str] = field(default_factory=set)
    cpu_total: float = 16.0
    memory_total: float = 64.0
    gpu_total: int = 0
    cost_per_hour: float = 0.0
    status: NodeStatus = NodeStatus.HEALTHY

    # Internal tracking
    _cpu_used: float = field(default=0.0, repr=False)
    _memory_used: float = field(default=0.0, repr=False)
    _gpu_used: int = field(default=0, repr=False)
    _workloads: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    _last_heartbeat: float = field(default_factory=time.time, repr=False)

    # --- Properties ---

    @property
    def cpu_available(self) -> float:
        return max(0.0, self.cpu_total - self._cpu_used)

    @property
    def memory_available(self) -> float:
        return max(0.0, self.memory_total - self._memory_used)

    @property
    def gpu_available(self) -> int:
        return max(0, self.gpu_total - self._gpu_used)

    @property
    def utilization(self) -> float:
        """Overall utilization as 0.0-1.0."""
        cpu_util = self._cpu_used / self.cpu_total if self.cpu_total else 0.0
        mem_util = self._memory_used / self.memory_total if self.memory_total else 0.0
        return (cpu_util + mem_util) / 2.0

    @property
    def workload_count(self) -> int:
        return len(self._workloads)

    @property
    def is_schedulable(self) -> bool:
        return self.status in (NodeStatus.HEALTHY, NodeStatus.DEGRADED)

    @property
    def last_heartbeat_age(self) -> float:
        return time.time() - self._last_heartbeat

    # --- Actions ---

    def allocate(self, workload_id: str, cpu: float, memory: float, gpu: int = 0) -> bool:
        """Try to allocate resources for a workload. Returns True on success."""
        if not self.is_schedulable:
            return False
        if cpu > self.cpu_available or memory > self.memory_available or gpu > self.gpu_available:
            return False
        self._cpu_used += cpu
        self._memory_used += memory
        self._gpu_used += gpu
        self._workloads[workload_id] = {
            "cpu": cpu, "memory": memory, "gpu": gpu,
            "allocated_at": time.time(),
        }
        return True

    def deallocate(self, workload_id: str) -> bool:
        """Release resources for a workload. Returns True if found."""
        if workload_id not in self._workloads:
            return False
        w = self._workloads.pop(workload_id)
        self._cpu_used = max(0.0, self._cpu_used - w["cpu"])
        self._memory_used = max(0.0, self._memory_used - w["memory"])
        self._gpu_used = max(0, self._gpu_used - w["gpu"])
        return True

    def heartbeat(self) -> None:
        """Update heartbeat timestamp."""
        self._last_heartbeat = time.time()

    def drain(self) -> None:
        """Mark node as draining (no new workloads)."""
        self.status = NodeStatus.DRAINING

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "labels": sorted(self.labels),
            "cpu_total": self.cpu_total,
            "memory_total": self.memory_total,
            "gpu_total": self.gpu_total,
            "cpu_available": self.cpu_available,
            "memory_available": self.memory_available,
            "gpu_available": self.gpu_available,
            "utilization": round(self.utilization, 3),
            "status": self.status.value,
            "workload_count": self.workload_count,
            "cost_per_hour": self.cost_per_hour,
        }
