import tomllib
from pathlib import Path

import pytest

from backend.config import Settings, load_settings


class TestLoadSettings:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        settings = load_settings(tmp_path / "nonexistent.toml")
        assert isinstance(settings, Settings)
        assert settings.log_level == "INFO"
        assert settings.orthanc.url == "http://orthanc:8042"

    def test_loads_valid_toml(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[system]
data_dir = "/custom/data"
log_level = "DEBUG"

[database]
url = "sqlite+aiosqlite:///./test.db"

[redis]
url = "redis://localhost:6380/1"

[orthanc]
url = "http://localhost:8042"
username = "admin"
password = "secret"
aet = "TESTNODE"

[gpu]
max_concurrent_inference = 4

[proknow]
base_url = "https://example.proknow.com"
credentials_file = "/creds.json"
"""
        )
        settings = load_settings(config_file)

        assert settings.data_dir == "/custom/data"
        assert settings.log_level == "DEBUG"
        assert settings.database_url == "sqlite+aiosqlite:///./test.db"
        assert settings.redis_url == "redis://localhost:6380/1"
        assert settings.orthanc.url == "http://localhost:8042"
        assert settings.orthanc.username == "admin"
        assert settings.orthanc.aet == "TESTNODE"
        assert settings.gpu.max_concurrent_inference == 4
        assert settings.proknow.base_url == "https://example.proknow.com"

    def test_partial_toml_fills_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[system]\nlog_level = \"WARNING\"\n")
        settings = load_settings(config_file)
        assert settings.log_level == "WARNING"
        # Unset sections get defaults
        assert settings.orthanc.url == "http://orthanc:8042"
        assert settings.gpu.max_concurrent_inference == 2

    def test_invalid_toml_raises(self, tmp_path):
        config_file = tmp_path / "bad.toml"
        config_file.write_text("this is not valid toml ][")
        with pytest.raises(tomllib.TOMLDecodeError):
            load_settings(config_file)
