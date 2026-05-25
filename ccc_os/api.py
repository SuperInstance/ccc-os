"""REST API server for CCC-OS fleet status.

Uses stdlib http.server — no external dependencies required.
Provides JSON endpoints for fleet status, alerts, tasks, and rubric testing.
"""

from __future__ import annotations

import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from .config import get_config
from .registry import get_registry
from .rubric import Input, Rubric
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class FleetAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for CCC-OS fleet API."""

    rubric: Rubric = None  # type: ignore
    orchestrator: Orchestrator = None  # type: ignore

    def log_message(self, format, *args):
        logger.info("API: %s", format % args)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = 400):
        self._send_json({"error": message, "status": status}, status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        if path == "/status":
            self._handle_status()
        elif path == "/alerts":
            self._handle_alerts()
        elif path == "/tasks":
            self._handle_tasks()
        elif path == "/monitors":
            self._handle_monitors()
        elif path == "/health":
            self._send_json({"status": "ok", "version": "2.0.0"})
        else:
            self._send_error(f"Unknown endpoint: {path}", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/rubric/test":
            self._handle_rubric_test()
        elif path == "/monitors/run":
            self._handle_monitors_run()
        else:
            self._send_error(f"Unknown endpoint: {path}", 404)

    def _handle_status(self):
        registry = get_registry()
        result = registry.run_all()
        self._send_json(result)

    def _handle_alerts(self):
        config = get_config()
        alerts_file = config.output_dir / "alerts.jsonl"
        alerts = []
        if alerts_file.exists():
            with open(alerts_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            alerts.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        self._send_json({"alerts": alerts, "count": len(alerts)})

    def _handle_tasks(self):
        config = get_config()
        tasks_file = config.output_dir / "task_queue.json"
        if tasks_file.exists():
            with open(tasks_file) as f:
                tasks = json.load(f)
            self._send_json({"tasks": tasks, "count": len(tasks) if isinstance(tasks, list) else 0})
        else:
            self._send_json({"tasks": [], "count": 0})

    def _handle_monitors(self):
        registry = get_registry()
        monitors = []
        for name in registry.list_monitors():
            info = registry.get_monitor_info(name)
            if info:
                monitors.append(info)
        self._send_json({"monitors": monitors, "count": len(monitors)})

    def _handle_rubric_test(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_error("Request body required")
            return
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self._send_error(f"Invalid JSON: {e}")
            return

        try:
            inp = Input(**data)
        except TypeError as e:
            self._send_error(f"Invalid input fields: {e}")
            return

        rubric = self.__class__.rubric or Rubric()
        result = rubric.score(inp)
        self._send_json({
            "decision": result.decision,
            "confidence": result.confidence.value,
            "score": result.score,
            "matched_rule": result.matched_rule,
            "explanation": result.explanation,
        })

    def _handle_monitors_run(self):
        registry = get_registry()
        result = registry.run_all()
        self._send_json(result)


def create_api_server(
    host: str = "0.0.0.0",
    port: int = 14001,
    rubric: Rubric | None = None,
    orchestrator: Orchestrator | None = None,
) -> HTTPServer:
    """Create an API server instance."""
    FleetAPIHandler.rubric = rubric or Rubric()
    FleetAPIHandler.orchestrator = orchestrator
    server = HTTPServer((host, port), FleetAPIHandler)
    return server


def run_api_server(
    host: str = "0.0.0.0",
    port: int = 14001,
    rubric: Rubric | None = None,
    background: bool = True,
) -> HTTPServer:
    """Start the API server. If background=True, runs in a daemon thread."""
    server = create_api_server(host, port, rubric)
    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info("API server started on %s:%d (background)", host, port)
    else:
        logger.info("API server started on %s:%d (foreground)", host, port)
        server.serve_forever()
    return server
