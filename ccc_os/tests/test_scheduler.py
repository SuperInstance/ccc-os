"""Tests for ccc_os.scheduler module."""

import time
import pytest
from ccc_os.node import ComputeNode, NodeStatus
from ccc_os.constraint import (
    AffinityConstraint, BudgetConstraint, ConstraintSeverity,
    DeadlineConstraint, DependencyConstraint, ResourceConstraint,
)
from ccc_os.resource import ResourceManager
from ccc_os.scheduler import ConstraintScheduler, ScheduleResult, Task, TaskState


def _make_scheduler(n_nodes: int = 2, cpu: float = 16.0, mem: float = 64.0, gpu: int = 0) -> ConstraintScheduler:
    rm = ResourceManager()
    for i in range(n_nodes):
        rm.add_node(ComputeNode(
            f"n{i}", cpu_total=cpu, memory_total=mem, gpu_total=gpu,
            labels={"gpu"} if i == 0 else set(),
        ))
    return ConstraintScheduler(rm)


class TestTask:
    def test_default_task(self):
        t = Task("t1")
        assert t.cpu == 1.0
        assert t.state == TaskState.PENDING

    def test_satisfies_constraints_empty(self):
        t = Task("t1")
        ok, penalty = t.satisfies_constraints({})
        assert ok is True
        assert penalty == 0.0

    def test_satisfies_constraints_with_resource(self):
        t = Task("t1", cpu=4, memory=8, constraints=[
            ResourceConstraint(min_cpu=4, min_memory=8),
        ])
        ok, pen = t.satisfies_constraints({"available_cpu": 8, "available_memory": 16, "available_gpu": 0})
        assert ok is True

    def test_fails_hard_constraint(self):
        t = Task("t1", constraints=[
            ResourceConstraint(min_cpu=999, severity=ConstraintSeverity.HARD),
        ])
        ok, pen = t.satisfies_constraints({"available_cpu": 1, "available_memory": 1, "available_gpu": 0})
        assert ok is False
        assert pen > 0


class TestConstraintScheduler:
    def test_schedule_single_task(self):
        s = _make_scheduler(1)
        task = Task("t1", cpu=4, memory=8)
        s.submit(task)
        result = s.schedule()
        assert result.scheduled is True
        assert result.node_id == "n0"
        assert task.state == TaskState.SCHEDULED

    def test_schedule_no_nodes(self):
        s = ConstraintScheduler()  # Empty resource manager
        s.submit(Task("t1", cpu=4, memory=8))
        result = s.schedule()
        assert result.scheduled is False

    def test_schedule_insufficient_resources(self):
        s = _make_scheduler(1, cpu=4, mem=8)
        s.submit(Task("t1", cpu=100, memory=8))
        result = s.schedule()
        assert result.scheduled is False
        assert "sufficient" in result.reason.lower() or "No nodes" in result.reason

    def test_schedule_priority_order(self):
        s = _make_scheduler(1, cpu=16, mem=128)
        s.submit(Task("low", cpu=8, memory=32, priority=5))
        s.submit(Task("high", cpu=8, memory=32, priority=1))
        results = s.schedule_all()
        # High priority should be scheduled first
        assert results[0].task_id == "high"

    def test_schedule_all(self):
        s = _make_scheduler(2)
        s.submit(Task("t1", cpu=4, memory=8))
        s.submit(Task("t2", cpu=4, memory=8))
        s.submit(Task("t3", cpu=4, memory=8))
        results = s.schedule_all()
        assert all(r.scheduled for r in results)
        assert s.scheduled_count == 3

    def test_cancel_pending(self):
        s = _make_scheduler(1)
        task = Task("t1", cpu=4, memory=8)
        s.submit(task)
        assert s.cancel("t1") is True
        assert task.state == TaskState.CANCELLED

    def test_cancel_nonexistent(self):
        s = _make_scheduler(1)
        assert s.cancel("ghost") is False

    def test_mark_completed(self):
        s = _make_scheduler(1)
        task = Task("t1", cpu=4, memory=8)
        s.submit(task)
        s.schedule()
        assert s.mark_completed("t1") is True
        assert task.state == TaskState.COMPLETED
        assert s.completed_count == 1

    def test_dependency_constraint(self):
        s = _make_scheduler(1)
        t1 = Task("t1", cpu=4, memory=8)
        t2 = Task("t2", cpu=4, memory=8, constraints=[
            DependencyConstraint(depends_on=frozenset({"t1"})),
        ])
        s.submit(t2)
        result = s.schedule(t2)
        assert result.scheduled is False
        assert "Dependen" in result.reason

    def test_dependency_satisfied_after_completion(self):
        s = _make_scheduler(1, cpu=16, mem=128)
        t1 = Task("t1", cpu=4, memory=8)
        t2 = Task("t2", cpu=4, memory=8, constraints=[
            DependencyConstraint(depends_on=frozenset({"t1"})),
        ])
        s.submit(t1)
        s.schedule()
        s.mark_completed("t1")
        s.submit(t2)
        result = s.schedule(t2)
        assert result.scheduled is True

    def test_affinity_constraint(self):
        s = _make_scheduler(2)
        s.rm.get_node("n0").labels = {"gpu"}
        s.rm.get_node("n1").labels = set()
        task = Task("t1", cpu=4, memory=8, constraints=[
            AffinityConstraint(required_labels=frozenset({"gpu"}), severity=ConstraintSeverity.HARD),
        ])
        s.submit(task)
        result = s.schedule()
        assert result.scheduled is True
        assert result.node_id == "n0"

    def test_budget_constraint(self):
        s = _make_scheduler(1)
        task = Task("t1", cpu=4, memory=8, estimated_cost=200.0, constraints=[
            BudgetConstraint(max_cost=100.0),
        ])
        s.submit(task)
        result = s.schedule()
        assert result.scheduled is False

    def test_to_dict(self):
        s = _make_scheduler(1)
        s.submit(Task("t1"))
        d = s.to_dict()
        assert "tasks" in d
        assert d["pending"] == 1

    def test_pending_count(self):
        s = _make_scheduler(1)
        s.submit(Task("t1"))
        s.submit(Task("t2"))
        assert s.pending_count == 2
        s.schedule()
        assert s.pending_count == 1
