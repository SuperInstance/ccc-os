"""Tests for ccc_os.node module."""

import time
import pytest
from ccc_os.node import ComputeNode, NodeStatus


class TestComputeNode:
    def test_default_node(self):
        n = ComputeNode("n1")
        assert n.node_id == "n1"
        assert n.cpu_total == 16.0
        assert n.memory_total == 64.0
        assert n.gpu_total == 0
        assert n.status == NodeStatus.HEALTHY

    def test_custom_node(self):
        n = ComputeNode("gpu-1", labels={"gpu", "a100"}, cpu_total=32, memory_total=256, gpu_total=4, cost_per_hour=3.50)
        assert n.gpu_total == 4
        assert "a100" in n.labels
        assert n.cost_per_hour == 3.50

    def test_available_resources(self):
        n = ComputeNode("n1", cpu_total=16, memory_total=64, gpu_total=2)
        assert n.cpu_available == 16.0
        assert n.memory_available == 64.0
        assert n.gpu_available == 2

    def test_allocate_success(self):
        n = ComputeNode("n1", cpu_total=16, memory_total=64, gpu_total=2)
        ok = n.allocate("w1", cpu=4, memory=8, gpu=1)
        assert ok is True
        assert n.cpu_available == 12.0
        assert n.memory_available == 56.0
        assert n.gpu_available == 1
        assert n.workload_count == 1

    def test_allocate_insufficient(self):
        n = ComputeNode("n1", cpu_total=4, memory_total=8)
        assert n.allocate("w1", cpu=8, memory=4) is False
        assert n.workload_count == 0

    def test_allocate_multiple(self):
        n = ComputeNode("n1", cpu_total=16, memory_total=64)
        assert n.allocate("w1", cpu=8, memory=32)
        assert n.allocate("w2", cpu=8, memory=32)
        assert n.cpu_available == 0.0
        assert n.memory_available == 0.0
        assert n.workload_count == 2

    def test_allocate_exceeds(self):
        n = ComputeNode("n1", cpu_total=16, memory_total=64)
        n.allocate("w1", cpu=8, memory=32)
        assert n.allocate("w2", cpu=10, memory=40) is False

    def test_deallocate(self):
        n = ComputeNode("n1", cpu_total=16, memory_total=64)
        n.allocate("w1", cpu=8, memory=32)
        assert n.deallocate("w1") is True
        assert n.cpu_available == 16.0
        assert n.workload_count == 0

    def test_deallocate_nonexistent(self):
        n = ComputeNode("n1")
        assert n.deallocate("w999") is False

    def test_utilization(self):
        n = ComputeNode("n1", cpu_total=16, memory_total=64)
        assert n.utilization == 0.0
        n.allocate("w1", cpu=8, memory=32)
        assert 0.49 < n.utilization < 0.51

    def test_is_schedulable(self):
        n = ComputeNode("n1")
        assert n.is_schedulable is True
        n.status = NodeStatus.OFFLINE
        assert n.is_schedulable is False
        n.status = NodeStatus.DRAINING
        assert n.is_schedulable is False
        n.status = NodeStatus.DEGRADED
        assert n.is_schedulable is True

    def test_drain(self):
        n = ComputeNode("n1")
        n.drain()
        assert n.status == NodeStatus.DRAINING
        assert not n.is_schedulable

    def test_drained_node_rejects_allocation(self):
        n = ComputeNode("n1")
        n.drain()
        assert n.allocate("w1", cpu=1, memory=1) is False

    def test_heartbeat(self):
        n = ComputeNode("n1")
        assert n.last_heartbeat_age < 1.0

    def test_to_dict(self):
        n = ComputeNode("n1", labels={"gpu"}, cpu_total=32, memory_total=128, gpu_total=2, cost_per_hour=1.5)
        d = n.to_dict()
        assert d["node_id"] == "n1"
        assert d["gpu_total"] == 2
        assert d["cost_per_hour"] == 1.5
        assert "gpu" in d["labels"]
        assert d["status"] == "healthy"
