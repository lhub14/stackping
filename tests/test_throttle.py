"""Tests for stackping.throttle."""

from __future__ import annotations

import time

import pytest

from stackping.throttle import Throttle, ThrottlePolicy


# ---------------------------------------------------------------------------
# ThrottlePolicy
# ---------------------------------------------------------------------------

def test_policy_default_interval():
    policy = ThrottlePolicy()
    assert policy.min_interval == 300.0


def test_policy_custom_interval():
    policy = ThrottlePolicy(min_interval=60.0)
    assert policy.min_interval == 60.0


def test_policy_zero_interval_allowed():
    policy = ThrottlePolicy(min_interval=0)
    assert policy.min_interval == 0


def test_policy_negative_interval_raises():
    with pytest.raises(ValueError, match="min_interval"):
        ThrottlePolicy(min_interval=-1)


# ---------------------------------------------------------------------------
# Throttle.should_alert
# ---------------------------------------------------------------------------

def test_first_alert_always_allowed():
    t = Throttle(ThrottlePolicy(min_interval=300))
    assert t.should_alert("web", "down") is True


def test_repeated_alert_suppressed_within_interval():
    t = Throttle(ThrottlePolicy(min_interval=300))
    t.record_alert("web", "down")
    assert t.should_alert("web", "down") is False


def test_state_change_bypasses_throttle():
    t = Throttle(ThrottlePolicy(min_interval=300))
    t.record_alert("web", "down")
    assert t.should_alert("web", "up") is True


def test_alert_allowed_after_interval(monkeypatch):
    t = Throttle(ThrottlePolicy(min_interval=10))
    start = time.monotonic()
    monkeypatch.setattr("stackping.throttle.time.monotonic", lambda: start)
    t.record_alert("web", "down")

    # Simulate time passing beyond the interval
    monkeypatch.setattr("stackping.throttle.time.monotonic", lambda: start + 11)
    assert t.should_alert("web", "down") is True


def test_zero_interval_always_allows():
    t = Throttle(ThrottlePolicy(min_interval=0))
    t.record_alert("web", "down")
    assert t.should_alert("web", "down") is True


# ---------------------------------------------------------------------------
# Throttle.reset
# ---------------------------------------------------------------------------

def test_reset_single_service():
    t = Throttle(ThrottlePolicy(min_interval=300))
    t.record_alert("web", "down")
    t.record_alert("api", "down")
    t.reset("web")
    assert t.should_alert("web", "down") is True
    assert t.should_alert("api", "down") is False


def test_reset_all_services():
    t = Throttle(ThrottlePolicy(min_interval=300))
    t.record_alert("web", "down")
    t.record_alert("api", "down")
    t.reset()
    assert t.should_alert("web", "down") is True
    assert t.should_alert("api", "down") is True


def test_reset_nonexistent_service_is_noop():
    t = Throttle(ThrottlePolicy(min_interval=300))
    t.reset("nonexistent")  # should not raise
