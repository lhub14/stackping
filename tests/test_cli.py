"""Tests for stackping.cli."""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stackping.cli import build_parser, main


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "services.yaml"
    cfg.write_text(
        textwrap.dedent(
            """\
            webhook_url: https://hooks.example.com/test
            interval: 30
            services:
              - name: Example
                url: https://example.com
            """
        )
    )
    return cfg


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["services.yaml"])
    assert args.config == "services.yaml"
    assert args.log_level == "INFO"
    assert args.once is False


def test_build_parser_once_flag():
    parser = build_parser()
    args = parser.parse_args(["services.yaml", "--once"])
    assert args.once is True


def test_build_parser_log_level():
    parser = build_parser()
    args = parser.parse_args(["services.yaml", "--log-level", "DEBUG"])
    assert args.log_level == "DEBUG"


def test_main_missing_config_returns_1(tmp_path: Path):
    result = main([str(tmp_path / "nonexistent.yaml")])
    assert result == 1


def test_main_invalid_config_returns_1(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: valid: config: at: all")
    result = main([str(bad)])
    assert result == 1


def test_main_runs_once(config_file: Path):
    with patch("stackping.cli.run_forever") as mock_run:
        result = main([str(config_file), "--once"])
    assert result == 0
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs.get("run_once") is True


def test_main_keyboard_interrupt_returns_0(config_file: Path):
    with patch("stackping.cli.run_forever", side_effect=KeyboardInterrupt):
        result = main([str(config_file), "--once"])
    assert result == 0
