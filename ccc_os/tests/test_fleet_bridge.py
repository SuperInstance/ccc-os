"""Tests for ccc_os.fleet_bridge module."""

import json
import tempfile
from pathlib import Path

import pytest

from ccc_os.fleet_bridge import FleetBridgeLogger, is_bus_available


class TestBusAvailability:
    """Test FleetEventBus availability detection."""

    def test_is_bus_available_returns_bool(self):
        result = is_bus_available()
        assert isinstance(result, bool)


class TestFleetBridgeLogger:
    """Test FleetBridgeLogger JSONL writing."""

    def test_log_event_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "events.jsonl"
            bridge = FleetBridgeLogger(log_file, source="test")
            bridge.log_event({"event_type": "test_event", "key": "value"})
            assert log_file.exists()
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["event_type"] == "test_event"
            assert data["key"] == "value"

    def test_log_event_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "nested" / "dir" / "events.jsonl"
            bridge = FleetBridgeLogger(log_file)
            bridge.log_event({"event_type": "x"})
            assert log_file.exists()

    def test_log_event_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "events.jsonl"
            bridge = FleetBridgeLogger(log_file)
            bridge.log_event({"event_type": "first"})
            bridge.log_event({"event_type": "second"})
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 2

    def test_log_event_with_verdict_key(self):
        """When event_type is missing, should fall back to 'verdict' key."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "events.jsonl"
            bridge = FleetBridgeLogger(log_file)
            bridge.log_event({"verdict": "APPROVED", "data": 42})
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["verdict"] == "APPROVED"

    def test_log_event_default_str(self):
        """Non-serializable values should be handled by default=str."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "events.jsonl"
            bridge = FleetBridgeLogger(log_file)
            bridge.log_event({"event_type": "test", "path": Path("/some/path")})
            data = json.loads(log_file.read_text().strip())
            assert "/some/path" in data["path"]

    def test_emit_no_bus(self):
        """emit() should silently do nothing when bus is unavailable."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "events.jsonl"
            bridge = FleetBridgeLogger(log_file)
            # Should not raise
            bridge.emit("test_event", {"key": "value"})

    def test_custom_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "events.jsonl"
            bridge = FleetBridgeLogger(log_file, source="my-source")
            assert bridge.source == "my-source"
