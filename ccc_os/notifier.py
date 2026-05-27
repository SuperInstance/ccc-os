"""Multi-channel notification system for CCC-OS.

Supports Discord webhooks, Telegram, file-based alerts, and generic webhooks.
All channels are non-blocking and best-effort.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class Notification:
    """A notification to send."""

    def __init__(self, title: str, body: str, severity: str = "info", metadata: dict | None = None):
        self.title = title
        self.body = body
        self.severity = severity  # info, warning, critical
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "severity": self.severity,
            "timestamp": self.timestamp,
            **self.metadata,
        }


class Channel:
    """Base notification channel."""

    def __init__(self, name: str):
        self.name = name

    def send(self, notification: Notification) -> bool:
        raise NotImplementedError


class DiscordChannel(Channel):
    """Send notifications via Discord webhook."""

    def __init__(self, webhook_url: str):
        super().__init__("discord")
        self.webhook_url = webhook_url

    def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            return False
        try:
            color = {
                "critical": 15158332,  # red
                "warning": 16776960,   # yellow
                "info": 3447003,       # blue
            }.get(notification.severity, 3447003)

            payload = {
                "embeds": [{
                    "title": notification.title,
                    "description": notification.body[:2000],
                    "color": color,
                    "timestamp": notification.timestamp,
                    "footer": {"text": "CCC-OS"},
                }]
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status in (200, 204)
        except Exception as e:
            logger.warning("Discord notification failed: %s", e)
            return False


class TelegramChannel(Channel):
    """Send notifications via Telegram bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        super().__init__("telegram")
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, notification: Notification) -> bool:
        if not self.bot_token or not self.chat_id:
            return False
        try:
            severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
                notification.severity, "ℹ️"
            )
            text = f"{severity_emoji} *{notification.title}*\n\n{notification.body[:4000]}"
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status == 200
        except Exception as e:
            logger.warning("Telegram notification failed: %s", e)
            return False


class FileChannel(Channel):
    """Write notifications to a JSONL file."""

    def __init__(self, file_path: str | Path):
        super().__init__("file")
        self.file_path = Path(file_path)

    def send(self, notification: Notification) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "a") as f:
                f.write(json.dumps(notification.to_dict()) + "\n")
            return True
        except Exception as e:
            logger.warning("File notification failed: %s", e)
            return False


class WebhookChannel(Channel):
    """Send notifications to a generic webhook URL."""

    def __init__(self, url: str):
        super().__init__("webhook")
        self.url = url

    def send(self, notification: Notification) -> bool:
        if not self.url:
            return False
        try:
            data = json.dumps(notification.to_dict()).encode()
            req = urllib.request.Request(
                self.url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return 200 <= resp.status < 300
        except Exception as e:
            logger.warning("Webhook notification failed: %s", e)
            return False


class Notifier:
    """Multi-channel notification dispatcher."""

    def __init__(self):
        self.channels: list[Channel] = []

    def add_channel(self, channel: Channel) -> None:
        self.channels.append(channel)

    def notify(self, notification: Notification) -> dict[str, bool]:
        """Send notification to all channels. Returns per-channel results."""
        results = {}
        for channel in self.channels:
            try:
                results[channel.name] = channel.send(notification)
            except Exception as e:
                logger.warning("Channel %s failed: %s", channel.name, e)
                results[channel.name] = False
        return results

    def notify_simple(self, title: str, body: str, severity: str = "info") -> dict[str, bool]:
        """Convenience method for simple notifications."""
        return self.notify(Notification(title, body, severity))

    @classmethod
    def from_config(cls, config: dict[str, str], data_dir: Path | None = None) -> "Notifier":
        """Create a Notifier from config dict.

        Config keys: discord_webhook, telegram_bot_token, telegram_chat_id,
                     webhook_url, alert_file
        """
        notifier = cls()

        if config.get("discord_webhook"):
            notifier.add_channel(DiscordChannel(config["discord_webhook"]))

        if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
            notifier.add_channel(TelegramChannel(
                config["telegram_bot_token"], config["telegram_chat_id"]
            ))

        if config.get("webhook_url"):
            notifier.add_channel(WebhookChannel(config["webhook_url"]))

        alert_file = config.get("alert_file")
        if alert_file:
            notifier.add_channel(FileChannel(alert_file))
        elif data_dir:
            notifier.add_channel(FileChannel(data_dir / "alerts.jsonl"))

        return notifier
