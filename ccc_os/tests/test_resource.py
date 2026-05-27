"""Tests for ccc_os.resource module."""

from ccc_os.node import ComputeNode
from ccc_os.resource import FleetResources, ResourceManager


class TestFleetResources:
    def test_empty(self):
        fr = FleetResources()
        assert fr.available_cpu == 0.0
        assert fr.utilization == 0.0

    def test_available(self):
        fr = FleetResources(total_cpu=100.0, total_memory=500.0, total_gpu=10,
                            used_cpu=40.0, used_memory=200.0, used_gpu=4)
        assert fr.available_cpu == 60.0
        assert fr.available_memory == 300.0
        assert fr.available_gpu == 6

    def test_utilization(self):
        fr = FleetResources(total_cpu=100.0, used_cpu=50.0)
        assert fr.utilization == 0.5


class TestResourceManager:
    def _make_manager(self, n_nodes: int = 2) -> ResourceManager:
        rm = ResourceManager()
        for i in range(n_nodes):
            rm.add_node(ComputeNode(
                f"n{i}", cpu_total=16.0, memory_total=64.0, gpu_total=2,
                labels={"gpu"} if i == 0 else set(),
            ))
        return rm

    def test_add_node(self):
        rm = ResourceManager()
        rm.add_node(ComputeNode("n1"))
        assert rm.get_node("n1") is not None
        assert len(rm.nodes) == 1

    def test_remove_node(self):
        rm = self._make_manager(1)
        assert rm.remove_node("n0") is True
        assert rm.get_node("n0") is None

    def test_remove_node_with_workloads_fails(self):
        rm = self._make_manager(1)
        rm.allocate("w1", cpu=4, memory=8)
        assert rm.remove_node("n0") is False
        assert rm.remove_node("n0", force=True) is True

    def test_remove_nonexistent(self):
        rm = ResourceManager()
        assert rm.remove_node("ghost") is False

    def test_allocate_basic(self):
        rm = self._make_manager(1)
        alloc = rm.allocate("w1", cpu=4, memory=8)
        assert alloc is not None
        assert alloc.node_id == "n0"
        assert alloc.cpu == 4

    def test_allocate_preferred_node(self):
        rm = self._make_manager(3)
        alloc = rm.allocate("w1", cpu=4, memory=8, preferred_node="n2")
        assert alloc is not None
        assert alloc.node_id == "n2"

    def test_allocate_exclude_nodes(self):
        rm = self._make_manager(2)
        alloc = rm.allocate("w1", cpu=4, memory=8, exclude_nodes={"n0"})
        assert alloc is not None
        assert alloc.node_id == "n1"

    def test_allocate_least_utilized(self):
        rm = self._make_manager(2)
        rm.allocate("w1", cpu=12, memory=56, preferred_node="n0")  # Fill n0
        alloc = rm.allocate("w2", cpu=4, memory=8)  # Should go to n1
        assert alloc is not None
        assert alloc.node_id == "n1"

    def test_allocate_fails_insufficient(self):
        rm = self._make_manager(1)
        alloc = rm.allocate("w1", cpu=100, memory=8)
        assert alloc is None

    def test_deallocate(self):
        rm = self._make_manager(1)
        rm.allocate("w1", cpu=4, memory=8)
        assert rm.deallocate("w1") is True
        node = rm.get_node("n0")
        assert node.cpu_available == 16.0

    def test_deallocate_nonexistent(self):
        rm = ResourceManager()
        assert rm.deallocate("ghost") is False

    def test_fleet_resources(self):
        rm = self._make_manager(2)
        fr = rm.fleet_resources()
        assert fr.total_cpu == 32.0
        assert fr.total_memory == 128.0
        assert fr.total_gpu == 4
        assert fr.node_count == 2
        assert fr.healthy_count == 2

    def test_find_available(self):
        rm = self._make_manager(2)
        rm.get_node("n0").labels = {"gpu", "a100"}
        rm.get_node("n1").labels = set()
        found = rm.find_available(4, 8, gpu=1, labels={"gpu"})
        assert len(found) == 1
        assert found[0].node_id == "n0"

    def test_find_available_no_labels(self):
        rm = self._make_manager(2)
        found = rm.find_available(4, 8)
        assert len(found) == 2

    def test_find_available_insufficient(self):
        rm = self._make_manager(1)
        found = rm.find_available(100, 8)
        assert len(found) == 0

    def test_to_dict(self):
        rm = self._make_manager(1)
        d = rm.to_dict()
        assert "fleet" in d
        assert "nodes" in d
        assert d["fleet"]["node_count"] == 1
