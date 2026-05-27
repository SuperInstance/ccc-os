"""Tests for ccc_os.optimizer module."""

import pytest
from ccc_os.node import ComputeNode
from ccc_os.resource import ResourceManager
from ccc_os.optimizer import PlacementOptimizer, PlacementStrategy
from ccc_os.scheduler import Task
from ccc_os.constraint import (
    AffinityConstraint, BudgetConstraint, ConstraintSeverity,
    ResourceConstraint,
)


def _make_optimizer(n_nodes: int = 3) -> tuple[ResourceManager, PlacementOptimizer]:
    rm = ResourceManager()
    for i in range(n_nodes):
        rm.add_node(ComputeNode(
            f"n{i}", cpu_total=16.0, memory_total=64.0, gpu_total=2 if i == 0 else 0,
            labels={"gpu", "a100"} if i == 0 else set(),
            cost_per_hour=1.0 + i * 0.5,
        ))
    return rm, PlacementOptimizer(rm)


class TestPlacementOptimizer:
    def test_first_fit(self):
        rm, opt = _make_optimizer(2)
        tasks = [Task(f"t{i}", cpu=4, memory=8) for i in range(3)]
        result = opt.optimize(tasks, PlacementStrategy.FIRST_FIT)
        assert result.placed_count == 3
        assert len(result.unplaced) == 0

    def test_best_fit(self):
        rm, opt = _make_optimizer(3)
        tasks = [Task(f"t{i}", cpu=4, memory=8) for i in range(3)]
        result = opt.optimize(tasks, PlacementStrategy.BEST_FIT)
        assert result.placed_count == 3

    def test_spread(self):
        rm, opt = _make_optimizer(3)
        tasks = [Task(f"t{i}", cpu=4, memory=8) for i in range(3)]
        result = opt.optimize(tasks, PlacementStrategy.SPREAD)
        assert result.placed_count == 3
        # Spread should distribute across nodes
        node_ids = {p.node_id for p in result.placements}
        assert len(node_ids) >= 2

    def test_constraint_scored(self):
        rm, opt = _make_optimizer(3)
        tasks = [Task(f"t{i}", cpu=4, memory=8) for i in range(3)]
        result = opt.optimize(tasks, PlacementStrategy.CONSTRAINT_SCORED)
        assert result.placed_count == 3

    def test_strategy_by_string(self):
        rm, opt = _make_optimizer(2)
        tasks = [Task("t1", cpu=4, memory=8)]
        result = opt.optimize(tasks, "spread")
        assert result.placed_count == 1
        assert result.strategy_used == PlacementStrategy.SPREAD

    def test_unplaced_when_oversubscribed(self):
        rm, opt = _make_optimizer(1)
        # Node has 16 CPU, 64 mem — can fit 4 tasks of 4cpu/16mem
        tasks = [Task(f"t{i}", cpu=4, memory=16) for i in range(6)]
        result = opt.optimize(tasks, PlacementStrategy.BEST_FIT)
        assert result.placed_count == 4
        assert len(result.unplaced) == 2

    def test_largest_first_ordering(self):
        rm, opt = _make_optimizer(1)
        # Node: 16 cpu, 64 mem
        tasks = [
            Task("small", cpu=2, memory=4),
            Task("large", cpu=14, memory=56),
        ]
        result = opt.optimize(tasks, PlacementStrategy.FIRST_FIT)
        # Both should fit because large is placed first
        assert result.placed_count == 2

    def test_no_nodes(self):
        rm = ResourceManager()
        opt = PlacementOptimizer(rm)
        result = opt.optimize([Task("t1", cpu=4, memory=8)])
        assert result.placed_count == 0
        assert result.unplaced == ["t1"]

    def test_gpu_tasks(self):
        rm, opt = _make_optimizer(3)
        gpu_task = Task("gpu-t1", cpu=4, memory=8, gpu=1)
        result = opt.optimize([gpu_task], PlacementStrategy.BEST_FIT)
        assert result.placed_count == 1
        assert result.placements[0].node_id == "n0"  # Only n0 has GPU


class TestScoreNode:
    def test_score_good_fit(self):
        rm, opt = _make_optimizer(1)
        node = rm.get_node("n0")
        task = Task("t1", cpu=4, memory=8)
        score, penalty = opt.score_node(task, node)
        assert score > 0
        assert penalty == 0.0

    def test_score_cannot_fit(self):
        rm, opt = _make_optimizer(1)
        node = rm.get_node("n0")
        task = Task("t1", cpu=999, memory=999)
        score, penalty = opt.score_node(task, node)
        assert score < 0

    def test_score_with_constraint_violation(self):
        rm, opt = _make_optimizer(2)
        node = rm.get_node("n1")  # No gpu label
        task = Task("t1", cpu=4, memory=8, constraints=[
            AffinityConstraint(required_labels=frozenset({"gpu"}), severity=ConstraintSeverity.HARD),
        ])
        score, penalty = opt.score_node(task, node)
        assert score < 0  # Hard constraint violation → rejected
