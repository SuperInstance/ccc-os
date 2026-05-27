"""Tests for ccc_os.orchestrator module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from ccc_os.config import Config
from ccc_os.notifier import FileChannel, Notifier
from ccc_os.orchestrator import Orchestrator
from ccc_os.registry import MonitorRegistry
from ccc_os.rubric import Rubric


def _make_config(tmp: str) -> Config:
    """Create a Config pointing output/data dirs at tmp."""
    config_path = Path(tmp) / "config.yaml"
    config_path.write_text(yaml.dump({
        "ccc_os": {
            "data_dir": str(Path(tmp) / "data"),
        }
    }))
    return Config(config_path)


class TestOrchestrator:
    """Test Orchestrator pipeline."""

    def test_run_with_no_monitors(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            orch = Orchestrator(
                config=config,
                registry=MonitorRegistry(),
                rubric=Rubric(),
                notifier=Notifier(),
            )
            result = orch.run()
            assert "monitors" in result
            assert "alerts" in result
            assert "tasks" in result
            assert "elapsed_seconds" in result
            assert "timestamp" in result
            assert result["alerts"] == []
            assert result["tasks"] == []

    def test_run_creates_output_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            orch = Orchestrator(config=config, registry=MonitorRegistry(), notifier=Notifier())
            orch.run()
            assert config.output_dir.exists()
            assert config.data_dir.exists()

    def test_run_saves_task_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            orch = Orchestrator(config=config, registry=MonitorRegistry(), notifier=Notifier())
            orch.run()
            tasks_file = config.output_dir / "task_queue.json"
            assert tasks_file.exists()
            tasks = json.loads(tasks_file.read_text())
            assert isinstance(tasks, list)

    def test_run_with_alerts_scores_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            registry = MonitorRegistry()

            def mock_monitor():
                return {
                    "alerts": [{
                        "source": "test",
                        "reason": "critical issue",
                        "action": "TELL_NOW",
                    }]
                }

            registry.register("test_mon", mock_monitor)
            orch = Orchestrator(config=config, registry=registry, notifier=Notifier())
            result = orch.run()
            assert len(result["alerts"]) == 1
            assert "rubric_score" in result["alerts"][0]
            assert "rubric_confidence" in result["alerts"][0]

    def test_tell_now_generates_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            registry = MonitorRegistry()

            def alert_monitor():
                return {
                    "alerts": [{
                        "source": "breeder",
                        "reason": "service down",
                        "action": "TELL_NOW",
                    }]
                }

            registry.register("breeder", alert_monitor)
            orch = Orchestrator(config=config, registry=registry, notifier=Notifier())
            result = orch.run()
            assert len(result["tasks"]) >= 1
            task = result["tasks"][0]
            assert task["priority"] == 1
            assert "Review and act immediately" in task["action"]

    def test_high_score_generates_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            registry = MonitorRegistry()

            def alert_monitor():
                return {
                    "alerts": [{
                        "source": "test",
                        "reason": "something needs attention",
                        "action": "LOG",
                    }]
                }

            registry.register("test", alert_monitor)
            orch = Orchestrator(config=config, registry=registry, notifier=Notifier())
            result = orch.run()
            assert isinstance(result["tasks"], list)

    def test_notifies_on_tell_now(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            registry = MonitorRegistry()
            notifier = Notifier()
            notifier.add_channel(FileChannel(Path(tmp) / "nalerts.jsonl"))

            def alert_monitor():
                return {"alerts": [{"source": "s", "reason": "r", "action": "TELL_NOW"}]}

            registry.register("m", alert_monitor)
            orch = Orchestrator(config=config, registry=registry, notifier=notifier)
            orch.run()
            assert (Path(tmp) / "nalerts.jsonl").exists()

    def test_elapsed_seconds_is_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            orch = Orchestrator(config=config, registry=MonitorRegistry(), notifier=Notifier())
            result = orch.run()
            assert result["elapsed_seconds"] >= 0

    def test_writes_orchestrator_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            orch = Orchestrator(config=config, registry=MonitorRegistry(), notifier=Notifier())
            orch.run()
            log_file = config.output_dir / "orchestrator_log.jsonl"
            assert log_file.exists()
            data = json.loads(log_file.read_text().strip())
            assert data["event_type"] == "orchestrator_run"

    def test_merges_existing_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            config.output_dir.mkdir(parents=True, exist_ok=True)
            existing = [{"title": "old task", "priority": 5, "score": 1}]
            (config.output_dir / "task_queue.json").write_text(json.dumps(existing))

            orch = Orchestrator(config=config, registry=MonitorRegistry(), notifier=Notifier())
            result = orch.run()
            titles = [t["title"] for t in result["tasks"]]
            assert "old task" in titles

    def test_default_constructor(self):
        """Orchestrator() with no args should construct without error."""
        with tempfile.TemporaryDirectory() as tmp:
            with patch("ccc_os.orchestrator.get_config") as mock_cfg:
                mock_cfg.return_value = _make_config(tmp)
                orch = Orchestrator()
                assert orch.config is not None

    def test_tasks_sorted_by_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = _make_config(tmp)
            registry = MonitorRegistry()

            def multi_alert():
                return {
                    "alerts": [
                        {"source": "a", "reason": "high pri", "action": "TELL_NOW"},
                        {"source": "b", "reason": "low pri scored", "action": "LOG"},
                    ]
                }

            registry.register("multi", multi_alert)
            orch = Orchestrator(config=config, registry=registry, notifier=Notifier())
            result = orch.run()
            if len(result["tasks"]) >= 2:
                priorities = [t["priority"] for t in result["tasks"]]
                assert priorities == sorted(priorities)
