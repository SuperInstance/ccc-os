"""Tests for ccc_os.api module."""

import json
import threading
import time

import pytest

from ccc_os.api import create_api_server


class TestAPIEndpoints:
    """Test API endpoints via HTTP."""

    def _start_server(self, port=14099):
        server = create_api_server("127.0.0.1", port)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.2)
        return server

    def test_health_endpoint(self):
        import urllib.request
        server = self._start_server(14099)
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:14099/health")
            data = json.loads(resp.read())
            assert data["status"] == "ok"
            assert data["version"] == "2.0.0"
        finally:
            server.shutdown()

    def test_unknown_endpoint_404(self):
        import urllib.error
        import urllib.request
        server = self._start_server(14098)
        try:
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen("http://127.0.0.1:14098/nonexistent")
            assert exc_info.value.code == 404
        finally:
            server.shutdown()

    def test_status_endpoint(self):
        import urllib.request
        server = self._start_server(14097)
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:14097/status")
            data = json.loads(resp.read())
            assert "monitors" in data
        finally:
            server.shutdown()

    def test_monitors_endpoint(self):
        import urllib.request
        server = self._start_server(14096)
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:14096/monitors")
            data = json.loads(resp.read())
            assert "monitors" in data
            assert "count" in data
        finally:
            server.shutdown()

    def test_tasks_endpoint_empty(self):
        import urllib.request
        server = self._start_server(14095)
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:14095/tasks")
            data = json.loads(resp.read())
            assert data["tasks"] == []
            assert data["count"] == 0
        finally:
            server.shutdown()

    def test_alerts_endpoint_empty(self):
        import urllib.request
        server = self._start_server(14094)
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:14094/alerts")
            data = json.loads(resp.read())
            assert data["alerts"] == []
            assert data["count"] == 0
        finally:
            server.shutdown()

    def test_rubric_test_post(self):
        import urllib.request
        server = self._start_server(14093)
        try:
            payload = json.dumps({
                "source": "test",
                "title": "Test alert",
                "body": "body text",
                "is_blocker": True,
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:14093/rubric/test",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            assert "decision" in data
            assert "confidence" in data
            assert "score" in data
        finally:
            server.shutdown()

    def test_rubric_test_empty_body(self):
        import urllib.error
        import urllib.request
        server = self._start_server(14092)
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:14092/rubric/test",
                data=b"",
                headers={"Content-Length": "0"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 400
        finally:
            server.shutdown()

    def test_monitors_run_post(self):
        import urllib.request
        server = self._start_server(14091)
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:14091/monitors/run",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            assert "monitors" in data
        finally:
            server.shutdown()

    def test_create_api_server_returns_server(self):
        server = create_api_server("127.0.0.1", 14090)
        assert server is not None
        server.server_close()
