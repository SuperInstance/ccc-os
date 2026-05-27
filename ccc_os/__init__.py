"""CCC-OS — Autonomous fleet monitoring, decision, and action system.

Core modules:
    constraint  — Constraint types (deadline, budget, dependency, affinity)
    node        — ComputeNode with capacity, health, workload tracking
    resource    — ResourceManager for fleet-wide allocation
    scheduler   — ConstraintScheduler for resource-aware task scheduling
    optimizer   — PlacementOptimizer with bin-packing strategies
"""

__version__ = "2.1.0"
