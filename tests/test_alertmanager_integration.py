"""Integration-style tests for AlertManager with real Throttle + RetryPolicy."""
from __future__ import annotations

from unittest.mock import call, patch

import pytest

from stackping.alertmanager import AlertManager
from stackping.checker import CheckResult
from stackping.config import Service
from stackping.notifier import NotifyResult
from stackping.retry import RetryPolicy
from stackping.throttle import ThrottlePolicy


def svc(name="svc") -> Service:
    return Service(name=name, url="http://x.com", webhook="http://hook", interval=10)


def result(up=True) -> CheckResult:
    return CheckResult(up=up, status_code=200 if up else 500, latency_ms=5.0)


def test_retry_exhausted_returns_last_failure():
    """When all retries fail, the final failed NotifyResult is returned."""
    manager = AlertManager(
        retry_policy=RetryPolicy(attempts=3, backoff=0.0, max_backoff=0.0),
        throttle_policy=ThrottlePolicy(min_interval_seconds=0),
    )
    fail = NotifyResult(ok=False, error="err")
    with patch("stackping.alertmanager.send_notification", return_value=fail):
        r = manager.maybe_send(svc(), result(up=False))
    assert r is not None
    assert r.ok is False


def test_retry_succeeds_on_second_attempt():
    """Notification succeeds on retry; throttle is recorded."""
    manager = AlertManager(
        retry_policy=RetryPolicy(attempts=3, backoff=0.0, max_backoff=0.0),
        throttle_policy=ThrottlePolicy(min_interval_seconds=60),
    )
    responses = [NotifyResult(ok=False, error="fail"), NotifyResult(ok=True)]
    with patch("stackping.alertmanager.send_notification", side_effect=responses):
        r = manager.maybe_send(svc(), result())
    assert r is not None and r.ok is True
    # Throttle recorded: next call should be suppressed
    with patch("stackping.alertmanager.send_notification") as mock:
        suppressed = manager.maybe_send(svc(), result())
    mock.assert_not_called()
    assert suppressed is None


def test_zero_throttle_allows_every_call():
    manager = AlertManager(
        retry_policy=RetryPolicy(attempts=1, backoff=0.0, max_backoff=0.0),
        throttle_policy=ThrottlePolicy(min_interval_seconds=0),
    )
    ok = NotifyResult(ok=True)
    service = svc()
    res = result()
    with patch("stackping.alertmanager.send_notification", return_value=ok):
        r1 = manager.maybe_send(service, res)
        r2 = manager.maybe_send(service, res)
        r3 = manager.maybe_send(service, res)
    assert all(r is not None and r.ok for r in (r1, r2, r3))
