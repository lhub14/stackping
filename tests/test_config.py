"""Tests for stackping.config — YAML loading and validation."""

import textwrap
from pathlib import Path

import pytest

from stackping.config import Config, ConfigError, Service, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "services.yaml"
    p.write_text(textwrap.dedent(content))
    return p


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_load_minimal_config(tmp_path):
    cfg_file = write_yaml(tmp_path, """
        services:
          - name: Homepage
            url: https://example.com
    """)
    cfg = load_config(cfg_file)
    assert isinstance(cfg, Config)
    assert len(cfg.services) == 1
    svc = cfg.services[0]
    assert svc.name == "Homepage"
    assert svc.url == "https://example.com"
    assert svc.interval == 60
    assert svc.timeout == 10
    assert svc.expected_status == 200


def test_load_full_config(tmp_path):
    cfg_file = write_yaml(tmp_path, """
        default_interval: 30
        default_timeout: 5
        webhook_url: https://hooks.example.com/abc
        services:
          - name: API
            url: https://api.example.com/health
            interval: 15
            timeout: 3
            expected_status: 204
            tags: [production, api]
    """)
    cfg = load_config(cfg_file)
    assert cfg.webhook_url == "https://hooks.example.com/abc"
    assert cfg.default_interval == 30
    svc = cfg.services[0]
    assert svc.interval == 15
    assert svc.expected_status == 204
    assert "api" in svc.tags


def test_default_interval_inherited(tmp_path):
    cfg_file = write_yaml(tmp_path, """
        default_interval: 45
        services:
          - name: Site
            url: https://example.com
    """)
    cfg = load_config(cfg_file)
    assert cfg.services[0].interval == 45


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------

def test_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/path/services.yaml")


def test_missing_services_key_raises(tmp_path):
    cfg_file = write_yaml(tmp_path, "webhook_url: https://example.com\n")
    with pytest.raises(ConfigError, match="'services'"):
        load_config(cfg_file)


def test_service_missing_name_raises(tmp_path):
    cfg_file = write_yaml(tmp_path, """
        services:
          - url: https://example.com
    """)
    with pytest.raises(ConfigError, match="missing 'name'"):
        load_config(cfg_file)


def test_service_missing_url_raises(tmp_path):
    cfg_file = write_yaml(tmp_path, """
        services:
          - name: NoURL
    """)
    with pytest.raises(ConfigError, match="missing 'url'"):
        load_config(cfg_file)


def test_invalid_yaml_raises(tmp_path):
    cfg_file = tmp_path / "services.yaml"
    cfg_file.write_text("services: [unclosed")
    with pytest.raises(ConfigError, match="Failed to parse YAML"):
        load_config(cfg_file)
