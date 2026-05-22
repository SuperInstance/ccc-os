#!/usr/bin/env python3
"""
Tests for ccc-os/fleet_bridge.py
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Ensure ccc-os and sunset-ecosystem are importable
_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE / "ccc-os"))
sys.path.insert(0, str(_WORKSPACE / "sunset-ecosystem"))

import fleet_bridge


class TestFleetBridgeLogger:
    """Test suite for FleetBridgeLogger."""

    def test_jsonl_written_and_bus_emitted(self):
        """Event emitted to bus when bus is available."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.jsonl"

            mock_bus = MagicMock()
            bridge = fleet_bridge.FleetBridgeLogger(log_file, source="test")
            bridge._bus = mock_bus

            event = {"verdict": "ACT_NOW", "comment_id": "123", "author": "test"}
            bridge.log_event(event)

            # JSONL assertion
            lines = list(open(log_file))
            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["verdict"] == "ACT_NOW"
            assert parsed["comment_id"] == "123"

            # Bus assertion
            mock_bus.emit.assert_called_once()
            call_args, call_kwargs = mock_bus.emit.call_args
            emitted_dict = call_args[0]
            assert emitted_dict["type"] == "ACT_NOW"
            assert "comment_id" in emitted_dict
            assert call_kwargs.get("source") == "test"

    def test_graceful_fallback_no_bus(self):
        """Graceful fallback when bus is unavailable — no crash, JSONL still written."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.jsonl"
            bridge = fleet_bridge.FleetBridgeLogger(log_file, source="test")
            bridge._bus = None  # Simulate unavailable bus

            event = {"verdict": "ACT_NOW", "foo": "bar"}
            bridge.log_event(event)  # Must not raise

            lines = list(open(log_file))
            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["foo"] == "bar"

    def test_jsonl_written_when_bus_raises(self):
        """JSONL still written (non-regression) even if bus emit throws."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.jsonl"
            bridge = fleet_bridge.FleetBridgeLogger(log_file, source="test")

            mock_bus = MagicMock()
            mock_bus.emit.side_effect = RuntimeError("bus explosion")
            bridge._bus = mock_bus

            event = {"verdict": "ACT_NOW", "payload": "data"}
            bridge.log_event(event)  # Must not raise

            lines = list(open(log_file))
            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["verdict"] == "ACT_NOW"

    def test_event_type_precedence_over_verdict(self):
        """Explicit event_type takes precedence over verdict for bus emit."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.jsonl"
            mock_bus = MagicMock()
            bridge = fleet_bridge.FleetBridgeLogger(log_file, source="test")
            bridge._bus = mock_bus

            event = {"event_type": "AGENT_SPAWN", "verdict": "TRACK", "agent": "zc-scout"}
            bridge.log_event(event)

            call_args, _ = mock_bus.emit.call_args
            assert call_args[0]["type"] == "AGENT_SPAWN"

    def test_direct_emit_no_jsonl(self):
        """Direct emit() does NOT write to JSONL."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.jsonl"
            mock_bus = MagicMock()
            bridge = fleet_bridge.FleetBridgeLogger(log_file, source="test")
            bridge._bus = mock_bus

            bridge.emit("AGENT_STATUS", {"agent": "zc-scout", "tick": 42})

            # JSONL must be empty
            assert not log_file.exists() or log_file.read_text().strip() == ""
            # Bus must have been called
            mock_bus.emit.assert_called_once()
            call_args, _ = mock_bus.emit.call_args
            assert call_args[0]["type"] == "AGENT_STATUS"

    def test_multiple_events_append_to_jsonl(self):
        """Multiple log_event calls append, not overwrite."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.jsonl"
            bridge = fleet_bridge.FleetBridgeLogger(log_file, source="test")
            bridge._bus = None

            for i in range(3):
                bridge.log_event({"seq": i})

            lines = list(open(log_file))
            assert len(lines) == 3
            assert json.loads(lines[0])["seq"] == 0
            assert json.loads(lines[2])["seq"] == 2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
