import json
import sys
from pathlib import Path

# Import directly from the __main__.py file
_main_path = str(Path(__file__).resolve().parent.parent / "__main__.py")

# Use importlib to load the module
import importlib.util
spec = importlib.util.spec_from_file_location("ccc_os_main", _main_path)
ccc_os_main = importlib.util.module_from_spec(spec)
sys.modules["ccc_os_main"] = ccc_os_main
spec.loader.exec_module(ccc_os_main)

MonitorRegistry = ccc_os_main.MonitorRegistry
register_monitor = ccc_os_main.register_monitor
run_all_monitors = ccc_os_main.run_all_monitors


class TestMonitorRegistry:
    """Test the pluggable monitor registry."""

    def test_register_and_run(self):
        registry = MonitorRegistry()
        
        def check_a():
            return {"ok": True, "alerts": []}
        
        registry.register("test_a", check_a, priority="P0")
        assert registry.list_monitors() == ["test_a"]
        
        result = registry.run_all()
        assert result["monitors"]["test_a"]["ok"] is True
        assert result["monitors"]["test_a"]["priority"] == "P0"
        assert len(result["alerts"]) == 0

    def test_register_global_and_run(self):
        # Note: this mutates global state — fine for tests
        def check_b():
            return {"ok": False, "alerts": [{"action": "TELL_NOW", "reason": "fail"}]}
        
        register_monitor("test_b", check_b, priority="P1")
        result = run_all_monitors()
        # Monitor ran without exception = ok=True, but alerts extracted
        assert len(result["alerts"]) >= 1
        assert result["alerts"][0]["source"] == "test_b"
        assert result["alerts"][0]["action"] == "TELL_NOW"

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
        
        def check_ok():
            return {"ok": True}
        
        registry.register("ok", check_ok)
        result = registry.run_all()
        assert "checked_at" in result
        assert "T" in result["checked_at"]  # ISO format

    def test_multiple_monitors(self):
        registry = MonitorRegistry()
        
        def check_1():
            return {"ok": True, "alerts": []}
        
        def check_2():
            return {"ok": True, "alerts": []}
        
        registry.register("one", check_1, "P0")
        registry.register("two", check_2, "P2")
        
        result = registry.run_all()
        assert len(result["monitors"]) == 2
        assert result["monitors"]["one"]["priority"] == "P0"
        assert result["monitors"]["two"]["priority"] == "P2"
