"""CCC-OS configuration management.

Loads settings from YAML config files with environment variable overrides.
All paths are relative to the config file location or the package root.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG = {
    "ccc_os": {
        "data_dir": "./data",
        "log_level": "INFO",
        "monitors": {
            "breeder": {"enabled": True, "interval": 900},
            "discussion5": {"enabled": True, "interval": 300},
            "zc": {"enabled": True, "interval": 300},
            "health": {"enabled": True, "interval": 300},
            "constraint": {"enabled": True, "interval": 600},
        },
        "notifications": {
            "discord_webhook": "",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "webhook_url": "",
            "alert_file": "",
        },
        "fleet_bus": {
            "enabled": "auto",
        },
        "api": {
            "host": "0.0.0.0",
            "port": 14001,
        },
        "rubric": {
            "weights": {
                "blocker": 10.0,
                "breakthrough": 8.0,
                "architecture": 6.0,
                "numbers": 5.0,
                "routine": 0.5,
            },
        },
        "health_services": [
            {"name": "MUD", "host": "147.224.38.131", "port": 4042, "path": "/status"},
            {"name": "Arena", "host": "147.224.38.131", "port": 4044, "path": "/status"},
            {"name": "Grammar", "host": "147.224.38.131", "port": 4045, "path": "/status"},
            {"name": "PLATO Gate", "host": "147.224.38.131", "port": 8847, "path": "/status"},
            {"name": "PLATO Shell", "host": "147.224.38.131", "port": 8848, "path": "/"},
            {"name": "Rate-Attention", "host": "147.224.38.131", "port": 4056, "path": "/status"},
            {"name": "Skill Forge", "host": "147.224.38.131", "port": 4057, "path": "/status"},
            {"name": "Matrix Bridge", "host": "147.224.38.131", "port": 6168, "path": "/status"},
        ],
        "zc_log_dir": "",
        "discussion_repo": "SuperInstance/SuperInstance",
        "discussion_number": 5,
    }
}

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR} patterns with environment variable values."""
    def _replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, "")
    return _ENV_PATTERN.sub(_replace, value)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_strings(obj: Any) -> Any:
    """Recursively resolve ${ENV} patterns in string values."""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _resolve_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_strings(item) for item in obj]
    return obj


class Config:
    """CCC-OS configuration with YAML loading and env overrides."""

    def __init__(self, config_path: str | Path | None = None):
        self._data = _DEFAULT_CONFIG.copy()
        self._config_dir = Path.cwd()

        if config_path:
            config_path = Path(config_path)
            if config_path.exists():
                self._config_dir = config_path.parent
                with open(config_path) as f:
                    loaded = yaml.safe_load(f)
                if loaded and isinstance(loaded, dict):
                    self._data = _deep_merge(self._data, loaded)

        # Apply environment variable overrides
        self._data = _resolve_strings(self._data)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested config value by key path."""
        obj = self._data
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                return default
        return obj

    @property
    def data_dir(self) -> Path:
        """Resolved data directory path."""
        raw = self.get("ccc_os", "data_dir") or "./data"
        p = Path(raw)
        if not p.is_absolute():
            return (self._config_dir / p).resolve()
        return p

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def log_level(self) -> str:
        return self.get("ccc_os", "log_level") or "INFO"

    @property
    def api_host(self) -> str:
        return self.get("ccc_os", "api", "host") or "0.0.0.0"

    @property
    def api_port(self) -> int:
        return int(self.get("ccc_os", "api", "port") or 14001)

    @property
    def rubric_weights(self) -> dict[str, float]:
        return self.get("ccc_os", "rubric", "weights") or {}

    def monitor_config(self, name: str) -> dict:
        """Get configuration for a specific monitor."""
        return self.get("ccc_os", "monitors", name) or {"enabled": False, "interval": 300}

    def notification_channels(self) -> dict[str, str]:
        """Get all notification channel configs."""
        return self.get("ccc_os", "notifications") or {}

    def health_services(self) -> list[dict]:
        return self.get("ccc_os", "health_services") or []

    @property
    def fleet_bus_enabled(self) -> str:
        return self.get("ccc_os", "fleet_bus", "enabled") or "auto"

    @property
    def zc_log_dir(self) -> Path:
        raw = self.get("ccc_os", "zc_log_dir") or ""
        if raw:
            p = Path(raw)
            if not p.is_absolute():
                return (self._config_dir / p).resolve()
            return p
        return self.data_dir / "zc_logs"

    @property
    def discussion_repo(self) -> str:
        return self.get("ccc_os", "discussion_repo") or "SuperInstance/SuperInstance"

    @property
    def discussion_number(self) -> int:
        return int(self.get("ccc_os", "discussion_number") or 5)

    def as_dict(self) -> dict:
        """Return the full config as a dict."""
        return self._data.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create a Config from a dict (for testing)."""
        cfg = cls.__new__(cls)
        cfg._data = _deep_merge(_DEFAULT_CONFIG, data)
        cfg._config_dir = Path.cwd()
        return cfg


# Module-level default config
_default_config: Config | None = None


def get_config(config_path: str | Path | None = None) -> Config:
    """Get or create the default config singleton."""
    global _default_config
    if _default_config is None or config_path is not None:
        _default_config = Config(config_path)
    return _default_config
