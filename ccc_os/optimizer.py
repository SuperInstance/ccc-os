"""PlacementOptimizer — Bin-packing and constraint-based placement optimization.

Provides strategies for optimizing task placement across the fleet:
- First Fit Decreasing (bin-packing)
- Best Fit (tightest fit)
- Spread (distribute evenly)
- Constraint-aware scoring
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from .constraint import ConstraintSeverity
from .node import ComputeNode
from .resource import ResourceManager
from .scheduler import Task

logger = logging.getLogger(__name__)


class PlacementStrategy(Enum):
    """Available placement strategies."""
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"
    SPREAD = "spread"
    CONSTRAINT_SCORED = "constraint_scored"


@dataclass
class Placement:
    """A proposed task-to-node placement."""
    task_id: str
    node_id: str
    score: float = 0.0
    penalty: float = 0.0
    strategy: PlacementStrategy = PlacementStrategy.FIRST_FIT


@dataclass
class OptimizationResult:
    """Result of optimizing a batch of placements."""
    placements: list[Placement] = field(default_factory=list)
    unplaced: list[str] = field(default_factory=list)
    total_penalty: float = 0.0
    strategy_used: PlacementStrategy = PlacementStrategy.FIRST_FIT

    @property
    def placed_count(self) -> int:
        return len(self.placements)


class PlacementOptimizer:
    """Optimizes task placement across the fleet.

    Usage:
        rm = ResourceManager()
        rm.add_node(ComputeNode("n1", cpu_total=16, memory_total=64))
        rm.add_node(ComputeNode("n2", cpu_total=32, memory_total=128, gpu_total=4))
        opt = PlacementOptimizer(rm)
        result = opt.optimize([task1, task2, task3], strategy="best_fit")
    """

    def __init__(self, resource_manager: ResourceManager | None = None):
        self.rm = resource_manager or ResourceManager()

    def optimize(
        self,
        tasks: list[Task],
        strategy: str | PlacementStrategy = PlacementStrategy.BEST_FIT,
    ) -> OptimizationResult:
        """Optimize placement for a list of tasks.

        Tasks are sorted by size (largest resource request first) for bin-packing.

        Args:
            tasks: Tasks to place.
            strategy: Placement strategy name or enum.

        Returns:
            OptimizationResult with placements and unplaced tasks.
        """
        if isinstance(strategy, str):
            strategy = PlacementStrategy(strategy)

        # Sort tasks largest-first for bin-packing
        sorted_tasks = sorted(tasks, key=lambda t: t.cpu + t.memory, reverse=True)

        placer = {
            PlacementStrategy.FIRST_FIT: self._first_fit,
            PlacementStrategy.BEST_FIT: self._best_fit,
            PlacementStrategy.SPREAD: self._spread,
            PlacementStrategy.CONSTRAINT_SCORED: self._constraint_scored,
        }.get(strategy, self._best_fit)

        return placer(sorted_tasks, strategy)

    def score_node(self, task: Task, node: ComputeNode) -> tuple[float, float]:
        """Score a node for a task. Returns (score, penalty).

        Higher score = better fit. Lower penalty = fewer constraint violations.
        """
        score = 0.0
        penalty = 0.0

        # Resource fit score: prefer tight fit (less waste)
        if node.cpu_available >= task.cpu and node.memory_available >= task.memory and node.gpu_available >= task.gpu:
            cpu_waste = node.cpu_available - task.cpu
            mem_waste = node.memory_available - task.memory
            score = 100.0 - (cpu_waste * 0.5 + mem_waste * 0.3)
        else:
            return (-1.0, float("inf"))  # Can't fit

        # Utilization balance: prefer moderate utilization
        ideal_util = 0.7
        util_penalty = abs(node.utilization - ideal_util) * 20.0
        score -= util_penalty

        # Evaluate constraints
        context = {
            "now": 0.0,
            "estimated_finish": task.estimated_duration,
            "estimated_cost": task.estimated_cost,
            "completed_tasks": set(),
            "node_labels": node.labels,
            "available_cpu": node.cpu_available,
            "available_memory": node.memory_available,
            "available_gpu": node.gpu_available,
            "node_id": node.node_id,
        }
        for c in task.constraints:
            if not c.satisfied(context):
                if c.severity == ConstraintSeverity.HARD:
                    return (-1.0, float("inf"))
                penalty += c.penalty(context)
                score -= c.penalty(context) * 0.5

        return (score, penalty)

    def _get_candidates(self) -> list[ComputeNode]:
        """Get schedulable nodes sorted by node_id for determinism."""
        return sorted(
            [n for n in self.rm.nodes.values() if n.is_schedulable],
            key=lambda n: n.node_id,
        )

    def _first_fit(self, tasks: list[Task], strategy: PlacementStrategy) -> OptimizationResult:
        placements: list[Placement] = []
        unplaced: list[str] = []
        total_penalty = 0.0

        for task in tasks:
            placed = False
            for node in self._get_candidates():
                if node.cpu_available >= task.cpu and node.memory_available >= task.memory and node.gpu_available >= task.gpu:
                    score, penalty = self.score_node(task, node)
                    if score >= 0:
                        placements.append(Placement(
                            task_id=task.task_id, node_id=node.node_id,
                            score=score, penalty=penalty, strategy=strategy,
                        ))
                        # Simulate allocation for subsequent tasks
                        node.allocate(task.task_id, task.cpu, task.memory, task.gpu)
                        total_penalty += penalty
                        placed = True
                        break
            if not placed:
                unplaced.append(task.task_id)

        # Roll back simulated allocations
        for p in placements:
            node = self.rm.get_node(p.node_id)
            if node:
                node.deallocate(p.task_id)

        return OptimizationResult(
            placements=placements, unplaced=unplaced,
            total_penalty=total_penalty, strategy_used=strategy,
        )

    def _best_fit(self, tasks: list[Task], strategy: PlacementStrategy) -> OptimizationResult:
        placements: list[Placement] = []
        unplaced: list[str] = []
        total_penalty = 0.0

        for task in tasks:
            best: Placement | None = None
            best_node: ComputeNode | None = None
            best_score = float("-inf")

            for node in self._get_candidates():
                score, penalty = self.score_node(task, node)
                if score >= 0 and score > best_score:
                    best_score = score
                    best = Placement(
                        task_id=task.task_id, node_id=node.node_id,
                        score=score, penalty=penalty, strategy=strategy,
                    )
                    best_node = node

            if best and best_node:
                placements.append(best)
                best_node.allocate(task.task_id, task.cpu, task.memory, task.gpu)
                total_penalty += best.penalty
            else:
                unplaced.append(task.task_id)

        # Roll back simulated allocations
        for p in placements:
            node = self.rm.get_node(p.node_id)
            if node:
                node.deallocate(p.task_id)

        return OptimizationResult(
            placements=placements, unplaced=unplaced,
            total_penalty=total_penalty, strategy_used=strategy,
        )

    def _spread(self, tasks: list[Task], strategy: PlacementStrategy) -> OptimizationResult:
        placements: list[Placement] = []
        unplaced: list[str] = []
        total_penalty = 0.0

        for task in tasks:
            # Pick the least utilized node that fits
            candidates = [
                n for n in self._get_candidates()
                if n.cpu_available >= task.cpu
                and n.memory_available >= task.memory
                and n.gpu_available >= task.gpu
            ]
            if not candidates:
                unplaced.append(task.task_id)
                continue

            node = min(candidates, key=lambda n: n.utilization)
            score, penalty = self.score_node(task, node)
            placements.append(Placement(
                task_id=task.task_id, node_id=node.node_id,
                score=score, penalty=penalty, strategy=strategy,
            ))
            node.allocate(task.task_id, task.cpu, task.memory, task.gpu)
            total_penalty += penalty

        # Roll back simulated allocations
        for p in placements:
            node = self.rm.get_node(p.node_id)
            if node:
                node.deallocate(p.task_id)

        return OptimizationResult(
            placements=placements, unplaced=unplaced,
            total_penalty=total_penalty, strategy_used=strategy,
        )

    def _constraint_scored(self, tasks: list[Task], strategy: PlacementStrategy) -> OptimizationResult:
        """Like best_fit but with full constraint scoring."""
        return self._best_fit(tasks, strategy)
