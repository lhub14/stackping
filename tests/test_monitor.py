"""Tests for stackping.monitor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stackping.checker import CheckResult
from stackping.config import Config, Service
from stackping.monitor import _state, run_checks, _should_notify

WEBHOOK = "https://hooks.example.com/test"


def make_service(name="web", webhook=WEBHOOK):
    return Service(name=name, url="https://example.com", interval=60, timeout=5, expected_status=200, webhook=webhook)


def make_config(*services):
    return Config(services=list(services), default_interval=60, default_timeout=5)


def make_result(service, is_up=True):
    return CheckResult(service=service, is_up=is_up, status_code=200 if is_up else 503, latency_ms=10.0)


@pytest.fixture(autouse=True)
def clear_state():
    _state.clear()
    yield
    _state.clear()


# --- _should_notify ---

def test_should_notify_first_check_always_notifies():
    svc = make_service()
    result = make_result(svc, is_up=True)
    assert _should_notify(svc, result) is True


def test_should_notify_same_state_no_alert():
    svc = make_service()
    result = make_result(svc, is_up=True)
    _should_notify(svc, result)  # first call sets state
    assert _should_notify(svc, result) is False  # same state


def test_should_notify_state_change_triggers_alert():
    svc = make_service()
    up = make_result(svc, is_up=True)
    down = make_result(svc, is_up=False)
    _should_notify(svc, up)
    assert _should_notify(svc, down) is True


# --- run_checks ---

def test_run_checks_returns_results():
    svc = make_service()
    config = make_config(svc)
    fake_result = make_result(svc, is_up=True)

    with patch("stackping.monitor.check_service", return_value=fake_result) as mock_check, \
         patch("stackping.monitor.send_notification") as mock_notify:
        results = run_checks(config)

    assert len(results) == 1
    assert results[0] is fake_result
    mock_check.assert_called_once_with(svc)
    mock_notify.assert_called_once()


def test_run_checks_no_duplicate_notification_on_same_state():
    svc = make_service()
    config = make_config(svc)
    fake_result = make_result(svc, is_up=True)

    with patch("stackping.monitor.check_service", return_value=fake_result), \
         patch("stackping.monitor.send_notification") as mock_notify:
        run_checks(config)  # first pass — notifies
        run_checks(config)  # second pass — same state, no notify

    assert mock_notify.call_count == 1


def test_run_checks_no_webhook_skips_notification():
    svc = make_service(webhook=None)
    config = make_config(svc)
    fake_result = make_result(svc, is_up=False)

    with patch("stackping.monitor.check_service", return_value=fake_result), \
         patch("stackping.monitor.send_notification") as mock_notify:
        run_checks(config)

    mock_notify.assert_not_called()
