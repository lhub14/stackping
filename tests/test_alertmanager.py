"""Tests for stackping.alertmanager."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stackping.alertmanager import AlertManager
from stackping.checker import CheckResult
from stackping.config import Service
from stackping.notifier import NotifyResult
from stackping.retry import RetryPolicy
from stackping.throttle import ThrottlePolicy


def make_service(name: str = "web", webhook: str = "http://hook") -> Service:
    return Service(name=name, url="http://example.com", webhook=webhook, interval=60)


def make_result(up: bool = True) -> CheckResult:
    return CheckResult(up=up, status_code=200 if up else 500, latency_ms=42.0)


def ok_notify(service, result):
    return NotifyResult(ok=True)


def fail_notify(service, result):
    return NotifyResult(ok=False, error="timeout")


@pytest.fixture
def manager():
    return AlertManager(
        retry_policy=RetryPolicy(attempts=1, backoff=1.0, max_backoff=1.0),
        throttle_policy=ThrottlePolicy(min_interval_seconds=60),
    )


def test_maybe_send_first_call_sends(manager):
    service = make_service()
    result = make_result()
    with patch("stackping.alertmanager.send_notification", side_effect=ok_notify):
        notify = manager.maybe_send(service, result)
    assert notify is not None
    assert notify.ok is True


def test_maybe_send_throttled_on_second_call(manager):
    service = make_service()
    result = make_result()
    with patch("stackping.alertmanager.send_notification", side_effect=ok_notify):
        manager.maybe_send(service, result)
        second = manager.maybe_send(service, result)
    assert second is None


def test_maybe_send_failed_notify_does_not_record(manager):
    service = make_service()
    result = make_result(up=False)
    with patch("stackping.alertmanager.send_notification", side_effect=fail_notify):
        r1 = manager.maybe_send(service, result)
        r2 = manager.maybe_send(service, result)
    assert r1 is not None and r1.ok is False
    # throttle was NOT recorded, so second call should also attempt
    assert r2 is not None and r2.ok is False


def test_reset_clears_throttle(manager):
    service = make_service()
    result = make_result()
    with patch("stackping.alertmanager.send_notification", side_effect=ok_notify):
        manager.maybe_send(service, result)
        manager.reset(service.name)
        third = manager.maybe_send(service, result)
    assert third is not None and third.ok is True


def test_reset_unknown_service_is_noop(manager):
    manager.reset("nonexistent")  # should not raise


def test_multiple_services_independent_throttles(manager):
    svc_a = make_service(name="a")
    svc_b = make_service(name="b")
    result = make_result()
    with patch("stackping.alertmanager.send_notification", side_effect=ok_notify):
        r_a = manager.maybe_send(svc_a, result)
        r_b = manager.maybe_send(svc_b, result)
    assert r_a is not None and r_a.ok is True
    assert r_b is not None and r_b.ok is True
