"""Tests for stackping.notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from stackping.checker import CheckResult
from stackping.config import Service
from stackping.notifier import NotifyResult, build_payload, send_notification

WEBHOOK_URL = "https://hooks.example.com/notify"


def make_service(name="api", url="https://example.com", webhook=WEBHOOK_URL):
    return Service(name=name, url=url, interval=60, timeout=5, expected_status=200, webhook=webhook)


def make_result(is_up=True, status_code=200, latency_ms=42.5, error=None):
    svc = make_service()
    return CheckResult(service=svc, is_up=is_up, status_code=status_code, latency_ms=latency_ms, error=error)


# --- build_payload ---

def test_build_payload_up():
    result = make_result(is_up=True, status_code=200, latency_ms=30.1)
    payload = build_payload(result)
    assert payload["status"] == "UP"
    assert payload["service"] == "api"
    assert payload["http_status"] == 200
    assert payload["latency_ms"] == 30.1
    assert payload["error"] is None


def test_build_payload_down():
    result = make_result(is_up=False, status_code=503, latency_ms=None, error="Service Unavailable")
    payload = build_payload(result)
    assert payload["status"] == "DOWN"
    assert payload["error"] == "Service Unavailable"
    assert payload["latency_ms"] is None


def test_build_payload_no_status_code():
    result = make_result(is_up=False, status_code=None, error="timeout")
    payload = build_payload(result)
    assert "http_status" not in payload


# --- send_notification ---

def test_send_notification_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    with patch("stackping.notifier.requests.post", return_value=mock_response) as mock_post:
        result = send_notification(WEBHOOK_URL, make_result())

    assert result.success is True
    assert result.status_code == 200
    assert result.error is None
    mock_post.assert_called_once()


def test_send_notification_http_error():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")

    with patch("stackping.notifier.requests.post", return_value=mock_response):
        result = send_notification(WEBHOOK_URL, make_result())

    assert result.success is False
    assert "403 Forbidden" in result.error


def test_send_notification_connection_error():
    with patch("stackping.notifier.requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
        result = send_notification(WEBHOOK_URL, make_result())

    assert result.success is False
    assert result.error is not None


def test_notify_result_str_success():
    r = NotifyResult(success=True, status_code=204)
    assert "204" in str(r)


def test_notify_result_str_failure():
    r = NotifyResult(success=False, error="timeout")
    assert "timeout" in str(r)
