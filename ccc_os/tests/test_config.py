"""Tests for ccc_os.config module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from ccc_os.config import Config, get_config


class TestConfig:
    """Test configuration loading and resolution."""

    def test_default_config(self):
        config = Config()
        assert config.api_port == 14001
        assert config.api_host == "0.0.0.0"
        assert config.log_level == "INFO"

    def test_yaml_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(yaml.dump({
                "ccc_os": {
                    "api": {"port": 9999, "host": "127.0.0.1"},
                    "log_level": "DEBUG",
                }
            }))
            config = Config(config_path)
            assert config.api_port == 9999
            assert config.api_host == "127.0.0.1"
            assert config.log_level == "DEBUG"

    def test_env_var_resolution(self):
        os.environ["TEST_CCC_WEBHOOK"] = "https://discord.example.com/webhook"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.yaml"
                config_path.write_text(yaml.dump({
                    "ccc_os": {
                        "notifications": {
                            "discord_webhook": "${TEST_CCC_WEBHOOK}",
                        }
                    }
                }))
                config = Config(config_path)
                assert config.notification_channels()["discord_webhook"] == "https://discord.example.com/webhook"
        finally:
            del os.environ["TEST_CCC_WEBHOOK"]

    def test_data_dir_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(yaml.dump({
                "ccc_os": {"data_dir": "./mydata"}
            }))
            config = Config(config_path)
            assert config.data_dir == (Path(tmp) / "mydata").resolve()

    def test_data_dir_absolute(self):
        config = Config.from_dict({"ccc_os": {"data_dir": "/tmp/ccc-test"}})
        assert config.data_dir == Path("/tmp/ccc-test")

    def test_rubric_weights(self):
        config = Config.from_dict({
            "ccc_os": {
                "rubric": {
                    "weights": {"blocker": 99.0, "routine": 0.1}
                }
            }
        })
        weights = config.rubric_weights
        assert weights["blocker"] == 99.0
        assert weights["routine"] == 0.1

    def test_monitor_config(self):
        config = Config()
        mc = config.monitor_config("breeder")
        assert mc["enabled"] is True
        assert mc["interval"] == 900

    def test_unknown_monitor_config(self):
        config = Config()
        mc = config.monitor_config("nonexistent")
        assert mc["enabled"] is False

    def test_deep_merge(self):
        from ccc_os.config import _deep_merge
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 5}
        result = _deep_merge(base, override)
        assert result["a"]["b"] == 10
        assert result["a"]["c"] == 2
        assert result["d"] == 3
        assert result["e"] == 5

    def test_from_dict(self):
        config = Config.from_dict({"ccc_os": {"log_level": "WARNING"}})
        assert config.log_level == "WARNING"

    def test_get_config_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_health_services(self):
        config = Config()
        services = config.health_services()
        assert len(services) > 0
        assert services[0]["name"] == "MUD"

    def test_as_dict(self):
        config = Config()
        d = config.as_dict()
        assert "ccc_os" in d
