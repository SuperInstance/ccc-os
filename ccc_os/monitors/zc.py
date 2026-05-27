"""ZC Feed Monitor — Tracks zeroclaw agent logs and triages entries.

Reads ZC agent log files, extracts summaries, and triages for relevance.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..config import Config, get_config
from ..fleet_bridge import FleetBridgeLogger
from .base import BaseMonitor, MonitorResult

logger = logging.getLogger(__name__)


class ZCMonitor(BaseMonitor):
    """Monitor ZC (zeroclaw) agent feeds for fleet-relevant content."""

    name = "zc"
    priority = "P1"
    description = "Tracks zeroclaw agent logs and triages entries"

    HIGH_RELEVANCE = [
        "flux", "isa", "vm", "compiler", "verification",
        "safety", "certification", "asil", "constraint",
        "gpu", "cuda", "avx", "performance", "benchmark",
        "architecture", "protocol", "bridge", "nexus",
    ]

    MEDIUM_RELEVANCE = [
        "shell", "room", "mud", "plato", "tile", "gate",
        "agent", "spawn", "memory", "learning",
    ]

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._data_dir = self.config.data_dir / "zc"
        self._state_file = self._data_dir / "last_state.json"
        self._bridge = FleetBridgeLogger(
            self._data_dir / "zc_log.jsonl",
            source="ccc-os/zc-monitor",
        )

    def check(self) -> MonitorResult:
        """Scan ZC log files for new entries."""
        log_dir = self.config.zc_log_dir
        if not log_dir.exists():
            return MonitorResult(
                name=self.name, ok=True,
                status={"message": f"ZC log dir not found: {log_dir}"},
            )

        state = self._load_state()
        alerts = []
        summaries = []
        total_new = 0

        for log_file in sorted(log_dir.glob("zc-*.jsonl")):
            agent_name = log_file.stem
            last_tick = state.get(agent_name, 0)
            current_tick = self._get_last_tick(log_file)

            if current_tick <= last_tick:
                continue

            new_entries = self._get_entries_since(log_file, last_tick)
            if not new_entries:
                continue

            latest = new_entries[-1]
            summary = self._summarize(latest)
            verdict = self._triage(summary.get("topic", ""))

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": agent_name,
                "last_tick": last_tick,
                "current_tick": current_tick,
                "new_count": len(new_entries),
                "latest_summary": summary,
                "verdict": verdict,
            }
            self._bridge.log_event(event)
            summaries.append(event)

            if verdict == "ACT_NOW":
                alerts.append({
                    "action": "TELL_NOW",
                    "reason": f"[{agent_name}] {summary.get('topic', '')} — {summary.get('question_preview', '')[:80]}",
                    "source": "zc_feed",
                })

            state[agent_name] = current_tick
            total_new += len(new_entries)

        self._save_state(state)

        return MonitorResult(
            name=self.name,
            ok=len(alerts) == 0,
            status={"total_new": total_new, "agents_monitored": len(state)},
            alerts=alerts,
            data={"summaries": summaries},
        )

    def last_state(self) -> dict:
        return self._load_state()

    def _get_last_tick(self, filepath: Path) -> int:
        max_tick = 0
        try:
            with open(filepath) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        tick = data.get("tick", 0)
                        if tick > max_tick:
                            max_tick = tick
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass
        return max_tick

    def _get_entries_since(self, filepath: Path, min_tick: int) -> list[dict]:
        entries = []
        try:
            with open(filepath) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("tick", 0) > min_tick:
                            entries.append(data)
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass
        return entries

    def _summarize(self, entry: dict) -> dict:
        return {
            "agent": entry.get("agent", "unknown"),
            "topic": entry.get("topic", "unknown"),
            "tick": entry.get("tick", 0),
            "question_preview": entry.get("question", "")[:120],
            "timestamp": entry.get("timestamp", ""),
        }

    def _triage(self, topic: str) -> str:
        topic_lower = topic.lower()
        for keyword in self.HIGH_RELEVANCE:
            if keyword in topic_lower:
                return "ACT_NOW"
        for keyword in self.MEDIUM_RELEVANCE:
            if keyword in topic_lower:
                return "TRACK"
        return "IGNORE"

    def _load_state(self) -> dict:
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_state(self, state: dict) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)
