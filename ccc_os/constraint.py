"""Constraint types for CCC-OS constraint-aware scheduling.

Defines deadline, budget, dependency, and affinity constraints that
govern task placement and scheduling decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintType(Enum):
    """Supported constraint categories."""
    DEADLINE = "deadline"
    BUDGET = "budget"
    DEPENDENCY = "dependency"
    AFFINITY = "affinity"
    RESOURCE = "resource"


class ConstraintSeverity(Enum):
    """How strictly a constraint must be enforced."""
    HARD = "hard"       # Must be satisfied; violation rejects placement
    SOFT = "soft"       # Preferred; violation penalises score but doesn't reject
    PREFERENCE = "preference"  # Nice-to-have; minimal penalty


@dataclass(frozen=True)
class Constraint:
    """Base constraint applied to tasks or placements.

    Attributes:
        kind: The constraint category.
        severity: Enforcement level.
        name: Human-readable identifier.
        metadata: Arbitrary extra data.
    """
    kind: ConstraintType = ConstraintType.DEADLINE
    severity: ConstraintSeverity = ConstraintSeverity.HARD
    name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def satisfied(self, context: dict[str, Any]) -> bool:
        """Return True if this constraint is satisfied in *context*.

        The default implementation always returns True; subclasses override.
        """
        return True

    def penalty(self, context: dict[str, Any]) -> float:
        """Return a penalty score (0.0 = fully satisfied, higher = worse)."""
        if self.satisfied(context):
            return 0.0
        multipliers = {
            ConstraintSeverity.HARD: 1000.0,
            ConstraintSeverity.SOFT: 10.0,
            ConstraintSeverity.PREFERENCE: 1.0,
        }
        return multipliers.get(self.severity, 10.0)


@dataclass(frozen=True)
class DeadlineConstraint(Constraint):
    """Task must complete before a timestamp (epoch seconds)."""
    deadline: float = 0.0

    def __post_init__(self):
        if not self.kind or self.kind == ConstraintType.DEADLINE:
            object.__setattr__(self, "kind", ConstraintType.DEADLINE)

    def satisfied(self, context: dict[str, Any]) -> bool:
        now = context.get("now", 0.0)
        estimated_finish = context.get("estimated_finish", float("inf"))
        return estimated_finish <= self.deadline and now < self.deadline


@dataclass(frozen=True)
class BudgetConstraint(Constraint):
    """Maximum allowable cost (in arbitrary currency units)."""
    max_cost: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintType.BUDGET)

    def satisfied(self, context: dict[str, Any]) -> bool:
        estimated_cost = context.get("estimated_cost", float("inf"))
        return estimated_cost <= self.max_cost


@dataclass(frozen=True)
class DependencyConstraint(Constraint):
    """Task depends on other task IDs completing first."""
    depends_on: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintType.DEPENDENCY)

    def satisfied(self, context: dict[str, Any]) -> bool:
        completed: set[str] = context.get("completed_tasks", set())
        return self.depends_on.issubset(completed)


@dataclass(frozen=True)
class AffinityConstraint(Constraint):
    """Task prefers (or anti-prefers) specific nodes or labels.

    Set positive weight for affinity, negative for anti-affinity.
    """
    required_labels: frozenset[str] = field(default_factory=frozenset)
    anti_labels: frozenset[str] = field(default_factory=frozenset)
    weight: float = 1.0

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintType.AFFINITY)

    def satisfied(self, context: dict[str, Any]) -> bool:
        node_labels: set[str] = set(context.get("node_labels", set()))
        # Hard: all required labels must be present
        if self.severity == ConstraintSeverity.HARD:
            if not self.required_labels.issubset(node_labels):
                return False
        # Anti-affinity: must not have anti labels
        if self.anti_labels and self.anti_labels.intersection(node_labels):
            return False
        return True

    def penalty(self, context: dict[str, Any]) -> float:
        if self.satisfied(context):
            return 0.0
        base = super().penalty(context)
        return base * abs(self.weight)


@dataclass(frozen=True)
class ResourceConstraint(Constraint):
    """Minimum resource requirements (CPU cores, memory GB, GPU count)."""
    min_cpu: float = 0.0
    min_memory: float = 0.0
    min_gpu: int = 0

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintType.RESOURCE)

    def satisfied(self, context: dict[str, Any]) -> bool:
        avail_cpu = context.get("available_cpu", 0.0)
        avail_memory = context.get("available_memory", 0.0)
        avail_gpu = context.get("available_gpu", 0)
        return (
            avail_cpu >= self.min_cpu
            and avail_memory >= self.min_memory
            and avail_gpu >= self.min_gpu
        )
