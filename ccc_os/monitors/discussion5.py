"""Discussion Monitor — Polls GitHub discussions and auto-triages.

Polls a configured GitHub discussion, diffs against last state,
and triages into ACT_NOW / TRACK / IGNORE.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import Config, get_config
from ..rubric import Input, decide
from ..fleet_bridge import FleetBridgeLogger
from .base import BaseMonitor, MonitorResult

logger = logging.getLogger(__name__)


class DiscussionMonitor(BaseMonitor):
    """Monitor GitHub Discussions for fleet-relevant content."""

    name = "discussion5"
    priority = "P0"
    description = "Polls GitHub discussions and auto-triages new comments"

    ACT_SIGNALS = [
        "breakthrough", "beats the gpu", "beats the", "demolished",
        "blocker", "stuck on", "401", "403", "error", "critical",
        "new benchmark", "head-to-head", "throughput", "b/s",
        "architecture implication", "strategic implication",
        "paradigm shift", "certification", "asil", "dal",
        "question from", "need from you", "need casey",
    ]

    IGNORE_SIGNALS = [
        "next post at", "next check at", "monitoring every",
        "reply fires automatically", "routine", "status update only",
    ]

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._data_dir = self.config.data_dir / "discussion"
        self._state_file = self._data_dir / "last_state.json"
        self._bridge = FleetBridgeLogger(
            self._data_dir / "discussion_log.jsonl",
            source="ccc-os/discussion",
        )

    def check(self) -> MonitorResult:
        """Fetch and triage new discussion comments."""
        data = self._fetch_discussion()
        if not data:
            return MonitorResult(
                name=self.name, ok=False,
                error="Failed to fetch discussion",
            )

        discussion = data.get("data", {}).get("repository", {}).get("discussion", {})
        if not discussion:
            return MonitorResult(name=self.name, ok=False, error="No discussion data")

        comments = discussion.get("comments", {}).get("nodes", [])
        state = self._load_state()
        known_ids = set(state.get("comment_ids", []))

        new_comments = [c for c in comments if c.get("id") not in known_ids]

        alerts = []
        summaries = []
        for comment in new_comments:
            verdict = self._triage(comment)
            summary = self._format_summary(comment, verdict)

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "comment_id": comment.get("id"),
                "author": comment.get("author", {}).get("login", ""),
                "created_at": comment.get("createdAt", ""),
                "verdict": verdict,
                "summary": summary,
            }
            self._bridge.log_event(event)
            summaries.append(event)

            if verdict == "ACT_NOW":
                inp = Input(
                    source="discussion5",
                    title=summary[:80],
                    body=comment.get("body", "")[:500],
                    is_blocker=any(s in comment.get("body", "").lower() for s in ["blocker", "stuck", "error", "critical"]),
                    has_numbers=any(c.isdigit() for c in comment.get("body", "")),
                )
                decision = decide(inp)
                alerts.append({
                    "action": decision,
                    "reason": summary,
                    "source": "discussion5",
                })

        # Update state
        self._save_state({
            "comment_ids": [c.get("id") for c in comments],
            "last_check": datetime.now(timezone.utc).isoformat(),
        })

        return MonitorResult(
            name=self.name,
            ok=len(alerts) == 0,
            status={"new_comments": len(new_comments), "total_known": len(comments)},
            alerts=alerts,
            data={"summaries": summaries},
        )

    def last_state(self) -> dict:
        return self._load_state()

    def _fetch_discussion(self) -> dict | None:
        repo = self.config.discussion_repo
        number = self.config.discussion_number
        query = '''
        {
          repository(owner:"%s", name:"%s") {
            discussion(number:%d) {
              title
              comments(last:5) {
                nodes {
                  id
                  createdAt
                  author { login }
                  body
                }
              }
            }
          }
        }
        ''' % (repo.split("/")[0], repo.split("/")[1], number)

        try:
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error("gh failed: %s", result.stderr)
                return None
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            logger.error("Fetch failed: %s", e)
            return None

    def _triage(self, comment: dict) -> str:
        body = comment.get("body", "").lower()
        for signal in self.ACT_SIGNALS:
            if signal in body:
                return "ACT_NOW"
        for signal in self.IGNORE_SIGNALS:
            if signal in body:
                return "IGNORE"
        return "TRACK"

    def _format_summary(self, comment: dict, verdict: str) -> str:
        author = comment.get("author", {}).get("login", "")
        body = comment.get("body", "")
        title = ""
        for line in body.split("\n"):
            if line.startswith("##"):
                title = line.lstrip("# ")
                break
        if not title:
            title = f"Post by {author}"
        return f"**{title}** — by {author} | Verdict: **{verdict}**"

    def _load_state(self) -> dict:
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"comment_ids": [], "last_check": None}

    def _save_state(self, state: dict) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)
