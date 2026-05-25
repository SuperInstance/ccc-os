"""CCC-OS Orchestrator — Runs all monitors, applies rubric, generates outputs.

This is the main pipeline: Input → Rubric → Decision → Output.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Config, get_config
from .rubric import Input, Rubric
from .registry import MonitorRegistry
from .notifier import Notifier
from .fleet_bridge import FleetBridgeLogger

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator that runs monitors and generates outputs."""

    def __init__(
        self,
        config: Config | None = None,
        registry: MonitorRegistry | None = None,
        rubric: Rubric | None = None,
        notifier: Notifier | None = None,
    ):
        self.config = config or get_config()
        self.registry = registry or MonitorRegistry()
        self.rubric = rubric or Rubric(self.config.rubric_weights)
        self.notifier = notifier or Notifier.from_config(
            self.config.notification_channels(),
            self.config.data_dir,
        )
        self._bridge = FleetBridgeLogger(
            self.config.output_dir / "orchestrator_log.jsonl",
            source="ccc-os/orchestrator",
        )

    def run(self) -> dict[str, Any]:
        """Run the full orchestration pipeline."""
        start = time.time()
        logger.info("Orchestrator run starting at %s", datetime.now(timezone.utc).isoformat())

        # Ensure output dirs exist
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # Run all registered monitors
        monitor_results = self.registry.run_all()

        # Apply rubric to any alerts
        scored_alerts = []
        for alert in monitor_results.get("alerts", []):
            inp = Input(
                source=alert.get("source", "unknown"),
                title=alert.get("reason", "Unknown alert"),
                body=alert.get("reason", ""),
                is_blocker=alert.get("action") == "TELL_NOW",
            )
            result = self.rubric.score(inp)
            scored_alerts.append({
                **alert,
                "rubric_score": result.score,
                "rubric_confidence": result.confidence.value,
                "rubric_rule": result.matched_rule,
            })

        # Generate task queue
        tasks = self._generate_task_queue(monitor_results, scored_alerts)
        self._save_output("task_queue.json", tasks)

        # Notify on TELL_NOW alerts
        for alert in scored_alerts:
            if alert.get("action") == "TELL_NOW" or alert.get("rubric_score", 0) >= 5.0:
                self.notifier.notify_simple(
                    title=f"[{alert.get('source', 'unknown')}] {alert.get('reason', 'Alert')[:100]}",
                    body=alert.get("reason", "No details available"),
                    severity="critical" if alert.get("action") == "TELL_NOW" else "warning",
                )

        elapsed = time.time() - start

        result = {
            "monitors": monitor_results,
            "alerts": scored_alerts,
            "tasks": tasks,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._bridge.log_event({
            "event_type": "orchestrator_run",
            "elapsed": elapsed,
            "monitor_count": len(monitor_results.get("monitors", {})),
            "alert_count": len(scored_alerts),
            "task_count": len(tasks),
        })

        logger.info(
            "Orchestrator run complete: %d monitors, %d alerts, %d tasks in %.2fs",
            len(monitor_results.get("monitors", {})),
            len(scored_alerts),
            len(tasks),
            elapsed,
        )

        return result

    def _generate_task_queue(
        self,
        monitor_results: dict,
        scored_alerts: list[dict],
    ) -> list[dict]:
        """Generate prioritized task queue from monitor results."""
        tasks = []

        # Convert TELL_NOW/high-score alerts to tasks
        for alert in scored_alerts:
            if alert.get("action") in ("TELL_NOW",) or alert.get("rubric_score", 0) >= 5.0:
                tasks.append({
                    "source": alert.get("source", "unknown"),
                    "priority": 1 if alert.get("action") == "TELL_NOW" else 2,
                    "title": alert.get("reason", "Unknown")[:80],
                    "created": datetime.now(timezone.utc).isoformat(),
                    "action": "Review and act immediately" if alert.get("action") == "TELL_NOW" else "Review when available",
                    "score": alert.get("rubric_score", 0),
                })

        # Read existing task queue and merge
        existing_file = self.config.output_dir / "task_queue.json"
        if existing_file.exists():
            try:
                with open(existing_file) as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    # Add non-duplicate existing tasks
                    existing_titles = {t.get("title") for t in tasks}
                    for t in existing:
                        if t.get("title") not in existing_titles:
                            tasks.append(t)
            except (json.JSONDecodeError, OSError):
                pass

        tasks.sort(key=lambda t: (t.get("priority", 99), -t.get("score", 0)))
        return tasks

    def _save_output(self, filename: str, data: Any) -> None:
        path = self.config.output_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
