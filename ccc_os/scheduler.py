"""ConstraintScheduler — Resource-aware task scheduling with constraint satisfaction.

Accepts tasks with constraints and schedules them across the fleet using
the ResourceManager and PlacementOptimizer.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .constraint import (
    AffinityConstraint, BudgetConstraint, Constraint, ConstraintSeverity,
    ConstraintType, DeadlineConstraint, DependencyConstraint, ResourceConstraint,
)
from .node import ComputeNode
from .resource import ResourceManager

logger = logging.getLogger(__name__)


class TaskState(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A schedulable task.

    Attributes:
        task_id: Unique identifier.
        cpu: CPU cores required.
        memory: Memory in GB required.
        gpu: GPUs required.
        constraints: List of Constraint objects.
        priority: Lower = higher priority (0 = most urgent).
        estimated_duration: Expected runtime in seconds.
        estimated_cost: Expected cost in currency units.
        state: Current task state.
        assigned_node: Node ID once scheduled.
        created_at: Creation timestamp.
        deadline: Optional absolute deadline (epoch seconds).
    """
    task_id: str
    cpu: float = 1.0
    memory: float = 1.0
    gpu: int = 0
    constraints: list[Constraint] = field(default_factory=list)
    priority: int = 5
    estimated_duration: float = 60.0
    estimated_cost: float = 0.0
    state: TaskState = TaskState.PENDING
    assigned_node: str | None = None
    created_at: float = field(default_factory=time.time)
    deadline: float | None = None

    def satisfies_constraints(self, context: dict[str, Any]) -> tuple[bool, float]:
        """Check all constraints. Returns (all_satisfied, total_penalty)."""
        all_ok = True
        total_penalty = 0.0
        for c in self.constraints:
            if not c.satisfied(context):
                if c.severity == ConstraintSeverity.HARD:
                    all_ok = False
                total_penalty += c.penalty(context)
        return all_ok, total_penalty


@dataclass
class ScheduleResult:
    """Result of a scheduling attempt."""
    task_id: str
    scheduled: bool
    node_id: str | None = None
    reason: str = ""
    penalty: float = 0.0


class ConstraintScheduler:
    """Resource-aware constraint scheduler.

    Usage:
        rm = ResourceManager()
        rm.add_node(ComputeNode("n1", cpu_total=16, memory_total=64))
        scheduler = ConstraintScheduler(rm)
        result = scheduler.schedule(Task("t1", cpu=4, memory=8))
    """

    def __init__(self, resource_manager: ResourceManager | None = None):
        self.rm = resource_manager or ResourceManager()
        self._tasks: dict[str, Task] = {}
        self._completed: set[str] = set()
        self._schedule_order: list[str] = []

    def submit(self, task: Task) -> None:
        """Submit a task for scheduling."""
        self._tasks[task.task_id] = task
        logger.info("Submitted task %s (priority=%d, cpu=%.1f, mem=%.1f)",
                     task.task_id, task.priority, task.cpu, task.memory)

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or scheduled task."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.state in (TaskState.PENDING, TaskState.SCHEDULED):
            if task.assigned_node:
                self.rm.deallocate(task_id)
            task.state = TaskState.CANCELLED
            return True
        return False

    def schedule(self, task: Task | None = None) -> ScheduleResult:
        """Schedule a single task or the next best pending task.

        Args:
            task: Specific task to schedule. If None, picks the best pending task.

        Returns:
            ScheduleResult with placement details.
        """
        if task is None:
            task = self._pick_next()
        if task is None:
            return ScheduleResult("none", False, reason="No pending tasks")

        # Check dependency constraints
        dep_constraints = [c for c in task.constraints if c.kind == ConstraintType.DEPENDENCY]
        for dc in dep_constraints:
            ctx = {"completed_tasks": self._completed}
            if not dc.satisfied(ctx):
                return ScheduleResult(
                    task.task_id, False,
                    reason=f"Dependencies not met: {dc.depends_on - self._completed}",
                )

        # Find candidate nodes
        candidates = self.rm.find_available(task.cpu, task.memory, task.gpu)
        if not candidates:
            return ScheduleResult(
                task.task_id, False,
                reason="No nodes with sufficient resources",
            )

        # Score each candidate against constraints
        best_node = None
        best_penalty = float("inf")
        for node in candidates:
            context = self._build_context(task, node)
            all_ok, penalty = task.satisfies_constraints(context)
            if not all_ok:
                continue
            # Add utilization bias (prefer less loaded nodes)
            penalty += node.utilization * 0.1
            if penalty < best_penalty:
                best_penalty = penalty
                best_node = node

        if best_node is None:
            return ScheduleResult(
                task.task_id, False,
                reason="No node satisfies all hard constraints",
            )

        # Allocate
        alloc = self.rm.allocate(task.task_id, task.cpu, task.memory, task.gpu,
                                  preferred_node=best_node.node_id)
        if alloc is None:
            return ScheduleResult(task.task_id, False, reason="Allocation failed")

        task.state = TaskState.SCHEDULED
        task.assigned_node = best_node.node_id
        self._schedule_order.append(task.task_id)
        logger.info("Scheduled task %s on node %s (penalty=%.2f)",
                     task.task_id, best_node.node_id, best_penalty)
        return ScheduleResult(
            task.task_id, True,
            node_id=best_node.node_id,
            penalty=best_penalty,
        )

    def schedule_all(self) -> list[ScheduleResult]:
        """Schedule all pending tasks in priority order.

        Returns:
            List of ScheduleResults for each attempt.
        """
        results = []
        pending = [
            t for t in self._tasks.values()
            if t.state == TaskState.PENDING
        ]
        pending.sort(key=lambda t: (t.priority, t.created_at))
        for task in pending:
            results.append(self.schedule(task))
        return results

    def mark_completed(self, task_id: str) -> bool:
        """Mark a task as completed, releasing its resources."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        self.rm.deallocate(task_id)
        task.state = TaskState.COMPLETED
        task.assigned_node = None
        self._completed.add(task_id)
        return True

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.state == TaskState.PENDING)

    @property
    def scheduled_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.state == TaskState.SCHEDULED)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    def _pick_next(self) -> Task | None:
        """Pick the highest-priority pending task."""
        pending = [t for t in self._tasks.values() if t.state == TaskState.PENDING]
        if not pending:
            return None
        pending.sort(key=lambda t: (t.priority, t.created_at))
        return pending[0]

    def _build_context(self, task: Task, node: ComputeNode) -> dict[str, Any]:
        """Build constraint evaluation context for a task-node pair."""
        now = time.time()
        return {
            "now": now,
            "estimated_finish": now + task.estimated_duration,
            "estimated_cost": task.estimated_cost,
            "completed_tasks": self._completed,
            "node_labels": node.labels,
            "available_cpu": node.cpu_available,
            "available_memory": node.memory_available,
            "available_gpu": node.gpu_available,
            "node_id": node.node_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks": {
                tid: {
                    "task_id": t.task_id,
                    "state": t.state.value,
                    "priority": t.priority,
                    "assigned_node": t.assigned_node,
                    "cpu": t.cpu,
                    "memory": t.memory,
                    "gpu": t.gpu,
                }
                for tid, t in self._tasks.items()
            },
            "pending": self.pending_count,
            "scheduled": self.scheduled_count,
            "completed": self.completed_count,
        }
