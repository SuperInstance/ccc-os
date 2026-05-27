"""Tests for ccc_os.constraint module."""

from ccc_os.constraint import (
    AffinityConstraint,
    BudgetConstraint,
    Constraint,
    ConstraintSeverity,
    ConstraintType,
    DeadlineConstraint,
    DependencyConstraint,
    ResourceConstraint,
)


class TestDeadlineConstraint:
    def test_satisfied_when_before_deadline(self):
        c = DeadlineConstraint(deadline=100.0)
        assert c.satisfied({"now": 50.0, "estimated_finish": 80.0})

    def test_violated_when_past_deadline(self):
        c = DeadlineConstraint(deadline=100.0)
        assert not c.satisfied({"now": 50.0, "estimated_finish": 120.0})

    def test_violated_when_now_past_deadline(self):
        c = DeadlineConstraint(deadline=100.0)
        assert not c.satisfied({"now": 150.0, "estimated_finish": 80.0})

    def test_penalty_hard_violation(self):
        c = DeadlineConstraint(deadline=100.0, severity=ConstraintSeverity.HARD)
        assert c.penalty({"now": 200.0, "estimated_finish": 250.0}) > 0.0

    def test_penalty_satisfied(self):
        c = DeadlineConstraint(deadline=100.0)
        assert c.penalty({"now": 10.0, "estimated_finish": 50.0}) == 0.0

    def test_kind_is_deadline(self):
        c = DeadlineConstraint(deadline=100.0)
        assert c.kind == ConstraintType.DEADLINE

    def test_default_context(self):
        c = DeadlineConstraint(deadline=100.0)
        # Missing keys → estimated_finish=inf → violated
        assert not c.satisfied({})


class TestBudgetConstraint:
    def test_satisfied_under_budget(self):
        c = BudgetConstraint(max_cost=100.0)
        assert c.satisfied({"estimated_cost": 50.0})

    def test_violated_over_budget(self):
        c = BudgetConstraint(max_cost=100.0)
        assert not c.satisfied({"estimated_cost": 150.0})

    def test_exact_budget(self):
        c = BudgetConstraint(max_cost=100.0)
        assert c.satisfied({"estimated_cost": 100.0})

    def test_soft_penalty(self):
        c = BudgetConstraint(max_cost=100.0, severity=ConstraintSeverity.SOFT)
        p = c.penalty({"estimated_cost": 200.0})
        assert 0 < p < 1000  # Soft penalty is smaller than hard

    def test_kind_is_budget(self):
        c = BudgetConstraint(max_cost=50.0)
        assert c.kind == ConstraintType.BUDGET


class TestDependencyConstraint:
    def test_satisfied_when_deps_completed(self):
        c = DependencyConstraint(depends_on=frozenset({"t1", "t2"}))
        assert c.satisfied({"completed_tasks": {"t1", "t2", "t3"}})

    def test_violated_when_deps_missing(self):
        c = DependencyConstraint(depends_on=frozenset({"t1", "t2"}))
        assert not c.satisfied({"completed_tasks": {"t1"}})

    def test_no_deps_always_satisfied(self):
        c = DependencyConstraint(depends_on=frozenset())
        assert c.satisfied({"completed_tasks": set()})

    def test_empty_context(self):
        c = DependencyConstraint(depends_on=frozenset({"t1"}))
        assert not c.satisfied({})


class TestAffinityConstraint:
    def test_satisfied_required_labels(self):
        c = AffinityConstraint(required_labels=frozenset({"gpu", "us-west"}))
        assert c.satisfied({"node_labels": {"gpu", "us-west", "amd"}})

    def test_violated_missing_required_label(self):
        c = AffinityConstraint(
            required_labels=frozenset({"gpu"}),
            severity=ConstraintSeverity.HARD,
        )
        assert not c.satisfied({"node_labels": {"cpu-only"}})

    def test_anti_affinity(self):
        c = AffinityConstraint(anti_labels=frozenset({"spot"}))
        assert not c.satisfied({"node_labels": {"spot", "gpu"}})

    def test_soft_affinity_violated(self):
        c = AffinityConstraint(
            required_labels=frozenset({"gpu"}),
            severity=ConstraintSeverity.SOFT,
        )
        assert c.satisfied({"node_labels": {"cpu-only"}})  # Soft doesn't require

    def test_weighted_penalty(self):
        c = AffinityConstraint(
            anti_labels=frozenset({"spot"}),
            weight=2.0,
            severity=ConstraintSeverity.SOFT,
        )
        p = c.penalty({"node_labels": {"spot"}})
        assert p > 0


class TestResourceConstraint:
    def test_satisfied_with_enough(self):
        c = ResourceConstraint(min_cpu=4.0, min_memory=16.0, min_gpu=1)
        assert c.satisfied({"available_cpu": 8.0, "available_memory": 32.0, "available_gpu": 2})

    def test_violated_insufficient_cpu(self):
        c = ResourceConstraint(min_cpu=16.0, min_memory=8.0)
        assert not c.satisfied({"available_cpu": 4.0, "available_memory": 32.0, "available_gpu": 0})

    def test_violated_insufficient_gpu(self):
        c = ResourceConstraint(min_gpu=2)
        assert not c.satisfied({"available_cpu": 32.0, "available_memory": 128.0, "available_gpu": 1})

    def test_zero_requirements(self):
        c = ResourceConstraint()
        assert c.satisfied({"available_cpu": 0.0, "available_memory": 0.0, "available_gpu": 0})


class TestConstraintBase:
    def test_base_constraint_satisfied(self):
        c = Constraint(kind=ConstraintType.DEADLINE)
        assert c.satisfied({})

    def test_severity_defaults_hard(self):
        c = Constraint(kind=ConstraintType.DEADLINE)
        assert c.severity == ConstraintSeverity.HARD
