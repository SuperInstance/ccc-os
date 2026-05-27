"""Tests for ccc_os.notifier module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ccc_os.notifier import (
    Channel,
    DiscordChannel,
    FileChannel,
    Notification,
    Notifier,
    TelegramChannel,
    WebhookChannel,
)


class TestNotification:
    """Test Notification dataclass."""

    def test_basic_notification(self):
        n = Notification("Title", "Body text")
        assert n.title == "Title"
        assert n.body == "Body text"
        assert n.severity == "info"
        assert n.metadata == {}

    def test_notification_with_severity(self):
        n = Notification("T", "B", severity="critical")
        assert n.severity == "critical"

    def test_notification_with_metadata(self):
        n = Notification("T", "B", metadata={"key": "val"})
        assert n.metadata["key"] == "val"

    def test_to_dict(self):
        n = Notification("Title", "Body", severity="warning", metadata={"extra": 1})
        d = n.to_dict()
        assert d["title"] == "Title"
        assert d["body"] == "Body"
        assert d["severity"] == "warning"
        assert d["extra"] == 1
        assert "timestamp" in d

    def test_timestamp_iso_format(self):
        n = Notification("T", "B")
        assert "T" in n.timestamp  # ISO format contains T separator


class TestChannel:
    """Test Channel base class."""

    def test_base_channel_raises(self):
        ch = Channel("test")
        with pytest.raises(NotImplementedError):
            ch.send(Notification("T", "B"))


class TestFileChannel:
    """Test FileChannel."""

    def test_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alerts.jsonl"
            ch = FileChannel(path)
            n = Notification("Alert", "Something happened", severity="critical")
            result = ch.send(n)
            assert result is True
            data = json.loads(path.read_text().strip())
            assert data["title"] == "Alert"
            assert data["severity"] == "critical"

    def test_appends_multiple(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alerts.jsonl"
            ch = FileChannel(path)
            ch.send(Notification("A1", "B1"))
            ch.send(Notification("A2", "B2"))
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 2

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep" / "nested" / "alerts.jsonl"
            ch = FileChannel(path)
            assert ch.send(Notification("T", "B")) is True
            assert path.exists()


class TestDiscordChannel:
    """Test DiscordChannel."""

    def test_empty_url_returns_false(self):
        ch = DiscordChannel("")
        assert ch.send(Notification("T", "B")) is False

    def test_sends_with_correct_payload(self):
        ch = DiscordChannel("https://discord.example.com/webhook")
        n = Notification("Alert!", "Body text", severity="warning")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_urlopen.return_value = mock_resp
            result = ch.send(n)
            assert result is True
            # Verify the request was made
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data)
            assert payload["embeds"][0]["title"] == "Alert!"
            assert payload["embeds"][0]["color"] == 16776960  # yellow

    def test_critical_color(self):
        ch = DiscordChannel("https://example.com")
        n = Notification("T", "B", severity="critical")
        with patch("urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value = mock_resp
            ch.send(n)
            req = mock.call_args[0][0]
            payload = json.loads(req.data)
            assert payload["embeds"][0]["color"] == 15158332  # red

    def test_network_failure_returns_false(self):
        ch = DiscordChannel("https://example.com")
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            assert ch.send(Notification("T", "B")) is False


class TestTelegramChannel:
    """Test TelegramChannel."""

    def test_empty_token_returns_false(self):
        ch = TelegramChannel("", "chat123")
        assert ch.send(Notification("T", "B")) is False

    def test_empty_chat_id_returns_false(self):
        ch = TelegramChannel("token123", "")
        assert ch.send(Notification("T", "B")) is False

    def test_sends_successfully(self):
        ch = TelegramChannel("bot123", "chat456")
        n = Notification("Alert", "Details", severity="critical")
        with patch("urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value = mock_resp
            result = ch.send(n)
            assert result is True
            req = mock.call_args[0][0]
            assert "bot123" in req.full_url
            payload = json.loads(req.data)
            assert payload["chat_id"] == "chat456"
            assert "🔴" in payload["text"]

    def test_network_failure_returns_false(self):
        ch = TelegramChannel("tok", "chat")
        with patch("urllib.request.urlopen", side_effect=Exception("fail")):
            assert ch.send(Notification("T", "B")) is False


class TestWebhookChannel:
    """Test WebhookChannel."""

    def test_empty_url_returns_false(self):
        ch = WebhookChannel("")
        assert ch.send(Notification("T", "B")) is False

    def test_sends_successfully(self):
        ch = WebhookChannel("https://hooks.example.com/x")
        with patch("urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value = mock_resp
            assert ch.send(Notification("T", "B")) is True

    def test_2xx_success(self):
        ch = WebhookChannel("https://hooks.example.com/x")
        for status in (200, 201, 204, 299):
            with patch("urllib.request.urlopen") as mock:
                mock_resp = MagicMock()
                mock_resp.status = status
                mock.return_value = mock_resp
                assert ch.send(Notification("T", "B")) is True

    def test_non_2xx_failure(self):
        ch = WebhookChannel("https://hooks.example.com/x")
        with patch("urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 500
            mock.return_value = mock_resp
            assert ch.send(Notification("T", "B")) is False

    def test_network_failure_returns_false(self):
        ch = WebhookChannel("https://hooks.example.com/x")
        with patch("urllib.request.urlopen", side_effect=Exception("fail")):
            assert ch.send(Notification("T", "B")) is False


class TestNotifier:
    """Test Notifier multi-channel dispatcher."""

    def test_no_channels(self):
        n = Notifier()
        result = n.notify(Notification("T", "B"))
        assert result == {}

    def test_single_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            n = Notifier()
            n.add_channel(FileChannel(Path(tmp) / "alerts.jsonl"))
            result = n.notify(Notification("Test", "Body"))
            assert result["file"] is True

    def test_multiple_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            n = Notifier()
            n.add_channel(FileChannel(Path(tmp) / "a.jsonl"))
            n.add_channel(FileChannel(Path(tmp) / "b.jsonl"))
            result = n.notify(Notification("T", "B"))
            assert result["file"] is True  # both named "file"

    def test_notify_simple(self):
        with tempfile.TemporaryDirectory() as tmp:
            n = Notifier()
            n.add_channel(FileChannel(Path(tmp) / "alerts.jsonl"))
            result = n.notify_simple("Title", "Body", severity="warning")
            assert result["file"] is True

    def test_channel_exception_handled(self):
        n = Notifier()
        ch = MagicMock()
        ch.name = "mock_channel"
        ch.send.side_effect = RuntimeError("boom")
        n.add_channel(ch)
        result = n.notify(Notification("T", "B"))
        assert result["mock_channel"] is False

    def test_from_config_discord(self):
        n = Notifier.from_config({"discord_webhook": "https://discord.example.com"})
        assert len(n.channels) == 1
        assert isinstance(n.channels[0], DiscordChannel)

    def test_from_config_telegram(self):
        n = Notifier.from_config({
            "telegram_bot_token": "tok",
            "telegram_chat_id": "chat",
        })
        assert len(n.channels) == 1
        assert isinstance(n.channels[0], TelegramChannel)

    def test_from_config_webhook(self):
        n = Notifier.from_config({"webhook_url": "https://hooks.example.com"})
        assert len(n.channels) == 1
        assert isinstance(n.channels[0], WebhookChannel)

    def test_from_config_alert_file(self):
        n = Notifier.from_config({"alert_file": "/tmp/test_alerts.jsonl"})
        assert len(n.channels) == 1
        assert isinstance(n.channels[0], FileChannel)

    def test_from_config_data_dir_fallback(self):
        n = Notifier.from_config({}, data_dir=Path("/tmp/test_data"))
        assert len(n.channels) == 1
        assert isinstance(n.channels[0], FileChannel)

    def test_from_config_empty(self):
        n = Notifier.from_config({})
        # No channels without any config
        assert len(n.channels) == 0

    def test_from_config_all_channels(self):
        n = Notifier.from_config({
            "discord_webhook": "https://discord.example.com",
            "telegram_bot_token": "tok",
            "telegram_chat_id": "chat",
            "webhook_url": "https://hooks.example.com",
            "alert_file": "/tmp/test.jsonl",
        })
        assert len(n.channels) == 4
