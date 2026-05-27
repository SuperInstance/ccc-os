"""ResourceManager — Tracks CPU, memory, GPU allocations across the fleet.

Provides a centralized view of resource availability and handles
allocation/deallocation across multiple ComputeNodes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .node import ComputeNode, NodeStatus

logger = logging.getLogger(__name__)


@dataclass
class Allocation:
    """Record of a resource allocation."""
    allocation_id: str
    workload_id: str
    node_id: str
    cpu: float
    memory: float
    gpu: int


@dataclass
class FleetResources:
    """Aggregate fleet resource snapshot."""
    total_cpu: float = 0.0
    total_memory: float = 0.0
    total_gpu: int = 0
    used_cpu: float = 0.0
    used_memory: float = 0.0
    used_gpu: int = 0
    node_count: int = 0
    healthy_count: int = 0

    @property
    def available_cpu(self) -> float:
        return max(0.0, self.total_cpu - self.used_cpu)

    @property
    def available_memory(self) -> float:
        return max(0.0, self.total_memory - self.used_memory)

    @property
    def available_gpu(self) -> int:
        return max(0, self.total_gpu - self.used_gpu)

    @property
    def utilization(self) -> float:
        if self.total_cpu == 0:
            return 0.0
        return self.used_cpu / self.total_cpu


class ResourceManager:
    """Manages resource tracking across the fleet.

    Usage:
        rm = ResourceManager()
        rm.add_node(ComputeNode("n1", cpu_total=16, memory_total=64))
        ok = rm.allocate("task-1", cpu=4, memory=8)
    """

    def __init__(self):
        self._nodes: dict[str, ComputeNode] = {}
        self._allocations: dict[str, Allocation] = {}
        self._alloc_counter: int = 0

    # --- Node management ---

    def add_node(self, node: ComputeNode) -> None:
        """Register a compute node."""
        self._nodes[node.node_id] = node
        logger.info("Added node %s (cpu=%.1f, mem=%.1f, gpu=%d)",
                     node.node_id, node.cpu_total, node.memory_total, node.gpu_total)

    def remove_node(self, node_id: str, force: bool = False) -> bool:
        """Remove a node. Fails if node has workloads unless force=True."""
        node = self._nodes.get(node_id)
        if node is None:
            return False
        if node.workload_count > 0 and not force:
            logger.warning("Cannot remove node %s: %d workloads active",
                           node_id, node.workload_count)
            return False
        # Clean up allocations for this node
        to_remove = [aid for aid, a in self._allocations.items() if a.node_id == node_id]
        for aid in to_remove:
            del self._allocations[aid]
        del self._nodes[node_id]
        return True

    def get_node(self, node_id: str) -> ComputeNode | None:
        return self._nodes.get(node_id)

    @property
    def nodes(self) -> dict[str, ComputeNode]:
        return dict(self._nodes)

    # --- Allocation ---

    def allocate(
        self,
        workload_id: str,
        cpu: float,
        memory: float,
        gpu: int = 0,
        preferred_node: str | None = None,
        exclude_nodes: set[str] | None = None,
    ) -> Allocation | None:
        """Allocate resources for a workload on a suitable node.

        Args:
            workload_id: Identifier for the workload.
            cpu: CPU cores required.
            memory: Memory in GB required.
            gpu: Number of GPUs required.
            preferred_node: If set, try this node first.
            exclude_nodes: Nodes to skip.

        Returns:
            Allocation record on success, None on failure.
        """
        exclude = exclude_nodes or set()

        # Try preferred node first
        if preferred_node and preferred_node not in exclude:
            node = self._nodes.get(preferred_node)
            if node and node.allocate(workload_id, cpu, memory, gpu):
                return self._record_allocation(workload_id, node, cpu, memory, gpu)

        # Try all schedulable nodes sorted by least utilized
        candidates = sorted(
            [n for n in self._nodes.values()
             if n.node_id not in exclude and n.is_schedulable],
            key=lambda n: n.utilization,
        )
        for node in candidates:
            if node.allocate(workload_id, cpu, memory, gpu):
                return self._record_allocation(workload_id, node, cpu, memory, gpu)

        logger.warning("Failed to allocate workload %s (cpu=%.1f, mem=%.1f, gpu=%d)",
                       workload_id, cpu, memory, gpu)
        return None

    def deallocate(self, workload_id: str) -> bool:
        """Release resources for a workload."""
        alloc = self._allocations.get(workload_id)
        if alloc is None:
            return False
        node = self._nodes.get(alloc.node_id)
        if node:
            node.deallocate(workload_id)
        del self._allocations[workload_id]
        return True

    def _record_allocation(
        self, workload_id: str, node: ComputeNode,
        cpu: float, memory: float, gpu: int,
    ) -> Allocation:
        self._alloc_counter += 1
        alloc = Allocation(
            allocation_id=f"alloc-{self._alloc_counter}",
            workload_id=workload_id,
            node_id=node.node_id,
            cpu=cpu, memory=memory, gpu=gpu,
        )
        self._allocations[workload_id] = alloc
        return alloc

    # --- Fleet overview ---

    def fleet_resources(self) -> FleetResources:
        """Get aggregate fleet resource snapshot."""
        fr = FleetResources(node_count=len(self._nodes))
        for node in self._nodes.values():
            fr.total_cpu += node.cpu_total
            fr.total_memory += node.memory_total
            fr.total_gpu += node.gpu_total
            fr.used_cpu += node._cpu_used
            fr.used_memory += node._memory_used
            fr.used_gpu += node._gpu_used
            if node.status in (NodeStatus.HEALTHY, NodeStatus.DEGRADED):
                fr.healthy_count += 1
        return fr

    def find_available(
        self, cpu: float, memory: float, gpu: int = 0,
        labels: set[str] | None = None,
    ) -> list[ComputeNode]:
        """Find nodes that can satisfy a resource request.

        Args:
            cpu: Minimum CPU cores.
            memory: Minimum memory GB.
            gpu: Minimum GPUs.
            labels: Required labels (all must match).

        Returns:
            List of nodes sorted by utilization (least loaded first).
        """
        required = labels or set()
        candidates = []
        for node in self._nodes.values():
            if not node.is_schedulable:
                continue
            if not required.issubset(node.labels):
                continue
            if node.cpu_available >= cpu and node.memory_available >= memory and node.gpu_available >= gpu:
                candidates.append(node)
        return sorted(candidates, key=lambda n: n.utilization)

    def to_dict(self) -> dict[str, Any]:
        fr = self.fleet_resources()
        return {
            "fleet": {
                "total_cpu": fr.total_cpu,
                "total_memory": fr.total_memory,
                "total_gpu": fr.total_gpu,
                "used_cpu": fr.used_cpu,
                "used_memory": fr.used_memory,
                "used_gpu": fr.used_gpu,
                "node_count": fr.node_count,
                "healthy_count": fr.healthy_count,
            },
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "allocations": len(self._allocations),
        }
