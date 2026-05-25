"""Tests for ccc_os.monitors module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ccc_os.config import Config
from ccc_os.monitors.breeder import BreederMonitor
from ccc_os.monitors.health import HealthMonitor
from ccc_os.monitors.zc import ZCMonitor
from ccc_os.monitors.constraint import ConstraintMonitor
from ccc_os.monitors.base import BaseMonitor, MonitorResult


class TestBaseMonitor:

    def test_monitor_result_to_dict(self):
        result = MonitorResult(
            name="test", ok=True,
            status={"foo": "bar"},
            alerts=[{"action": "TELL_NOW", "reason": "test"}],
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["ok"] is True
        assert len(d["alerts"]) == 1

    def test_monitor_result_with_error(self):
        result = MonitorResult(name="test", ok=False, error="something failed")
        d = result.to_dict()
        assert d["error"] == "something failed"


class TestBreederMonitor:

    def test_healthy_state(self):
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test-breeder"}})
        monitor = BreederMonitor(config)
        result = monitor.check()
        assert result.ok is True
        assert result.name == "breeder"

    def test_critical_diversity(self):
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test-breeder-crit"}})
        monitor = BreederMonitor(config)
        monitor._synthetic_status = lambda: {
            "source": "synthetic",
            "diversity": 0.15,
            "thermal_pressure": 0.3,
            "active_agents": 12,
            "lifecycle_state": "COMPETE",
            "timestamp": 0,
        }
        result = monitor.check()
        assert result.ok is False
        assert len(result.alerts) >= 1

    def test_critical_thermal(self):
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test-breeder-thermal"}})
        monitor = BreederMonitor(config)
        monitor._synthetic_status = lambda: {
            "source": "synthetic",
            "diversity": 0.85,
            "thermal_pressure": 0.95,
            "active_agents": 12,
            "lifecycle_state": "COMPETE",
            "timestamp": 0,
        }
        result = monitor.check()
        assert result.ok is False

    def test_stalled_lifecycle(self):
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test-breeder-stall"}})
        monitor = BreederMonitor(config)
        monitor._synthetic_status = lambda: {
            "source": "synthetic",
            "diversity": 0.85,
            "thermal_pressure": 0.3,
            "active_agents": 0,
            "lifecycle_state": "STALLED",
            "timestamp": 0,
        }
        result = monitor.check()
        assert result.ok is False

    def test_run_compatibility(self):
        """Test that run() returns dict for registry compatibility."""
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test-breeder-run"}})
        monitor = BreederMonitor(config)
        result = monitor.run()
        assert isinstance(result, dict)
        assert "name" in result


class TestHealthMonitor:

    def test_no_services(self):
        config = Config.from_dict({
            "ccc_os": {
                "data_dir": "/tmp/ccc-test-health",
                "health_services": [],
            }
        })
        monitor = HealthMonitor(config)
        result = monitor.check()
        assert result.ok is True
        assert result.status["total"] == 0

    def test_with_mock_services(self):
        config = Config.from_dict({
            "ccc_os": {
                "data_dir": "/tmp/ccc-test-health2",
                "health_services": [
                    {"name": "Test", "host": "127.0.0.1", "port": 9999, "path": "/status"},
                ],
            }
        })
        monitor = HealthMonitor(config)
        # Service won't be running, so it'll be DOWN
        result = monitor.check()
        assert result.status["total"] == 1


class TestZCMonitor:

    def test_no_log_dir(self):
        config = Config.from_dict({
            "ccc_os": {
                "data_dir": "/tmp/ccc-test-zc",
                "zc_log_dir": "/tmp/nonexistent_zc_logs",
            }
        })
        monitor = ZCMonitor(config)
        result = monitor.check()
        assert result.ok is True  # No dir = no problems

    def test_with_log_files(self, tmp_path):
        log_dir = tmp_path / "zc_logs"
        log_dir.mkdir()
        log_file = log_dir / "zc-scout.jsonl"
        log_file.write_text(json.dumps({"tick": 1, "agent": "scout", "topic": "flux compiler"}) + "\n")

        config = Config.from_dict({
            "ccc_os": {
                "data_dir": str(tmp_path / "data"),
                "zc_log_dir": str(log_dir),
            }
        })
        monitor = ZCMonitor(config)
        result = monitor.check()
        assert result.status["total_new"] >= 1


class TestConstraintMonitor:

    def test_without_toolkit(self):
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test-constraint"}})
        monitor = ConstraintMonitor(config)
        result = monitor.check()
        # Without constraint-toolkit, returns ok with message
        assert result.ok is True
