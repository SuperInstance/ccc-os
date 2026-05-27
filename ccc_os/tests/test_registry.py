"""Tests for ccc_os.registry module."""

from ccc_os.registry import MonitorRegistry, get_registry, register_monitor


class TestMonitorRegistry:

    def test_register_and_run(self):
        registry = MonitorRegistry()
        registry.register("test_a", lambda: {"ok": True, "alerts": []}, priority="P0")
        assert registry.list_monitors() == ["test_a"]
        result = registry.run_all()
        assert result["monitors"]["test_a"]["ok"] is True
        assert result["monitors"]["test_a"]["priority"] == "P0"

    def test_failed_monitor(self):
        registry = MonitorRegistry()

        def check_fail():
            raise RuntimeError("boom")

        registry.register("fail", check_fail)
        result = registry.run_all()
        assert result["monitors"]["fail"]["ok"] is False
        assert "boom" in result["monitors"]["fail"]["error"]
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["action"] == "TELL_NOW"

    def test_empty_registry(self):
        registry = MonitorRegistry()
        result = registry.run_all()
        assert result["monitors"] == {}
        assert result["alerts"] == []

    def test_checked_at_timestamp(self):
        registry = MonitorRegistry()
        registry.register("ok", lambda: {"ok": True})
        result = registry.run_all()
        assert "checked_at" in result
        assert "T" in result["checked_at"]

    def test_multiple_monitors(self):
        registry = MonitorRegistry()
        registry.register("one", lambda: {"ok": True}, "P0")
        registry.register("two", lambda: {"ok": True}, "P2")
        result = registry.run_all()
        assert len(result["monitors"]) == 2
        assert result["monitors"]["one"]["priority"] == "P0"
        assert result["monitors"]["two"]["priority"] == "P2"

    def test_alerts_extraction(self):
        registry = MonitorRegistry()

        def check_with_alerts():
            return {
                "ok": False,
                "alerts": [
                    {"action": "TELL_NOW", "reason": "Something broke"},
                ],
            }

        registry.register("alerter", check_with_alerts)
        result = registry.run_all()
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["source"] == "alerter"

    def test_unregister(self):
        registry = MonitorRegistry()
        registry.register("temp", lambda: {"ok": True})
        assert "temp" in registry.list_monitors()
        assert registry.unregister("temp") is True
        assert "temp" not in registry.list_monitors()
        assert registry.unregister("nonexistent") is False

    def test_run_one(self):
        registry = MonitorRegistry()
        registry.register("a", lambda: {"ok": True}, "P0")
        registry.register("b", lambda: {"ok": True}, "P1")
        result = registry.run_one("a")
        assert result is not None
        assert result["ok"] is True
        assert registry.run_one("nonexistent") is None

    def test_get_monitor_info(self):
        registry = MonitorRegistry()
        registry.register("test", lambda: {"ok": True}, "P2")
        info = registry.get_monitor_info("test")
        assert info == {"name": "test", "priority": "P2"}
        assert registry.get_monitor_info("nonexistent") is None


class TestGlobalRegistry:

    def test_register_global(self):
        # The global registry is shared, so we just test it works
        register_monitor("test_global", lambda: {"ok": True}, priority="P2")
        registry = get_registry()
        assert "test_global" in registry.list_monitors()
