"""Tests for stackping.retry."""

from __future__ import annotations

import pytest

from stackping.retry import RetryPolicy, with_retry


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_retry_policy_delays_single_attempt():
    policy = RetryPolicy(attempts=1, backoff=2.0)
    assert policy.delays() == []


def test_retry_policy_delays_three_attempts():
    policy = RetryPolicy(attempts=3, backoff=2.0)
    assert policy.delays() == [2.0, 4.0]


def test_retry_policy_delays_capped_by_max_backoff():
    policy = RetryPolicy(attempts=5, backoff=10.0, max_backoff=15.0)
    delays = policy.delays()
    assert all(d <= 15.0 for d in delays)


def test_retry_policy_invalid_attempts():
    with pytest.raises(ValueError, match="attempts"):
        RetryPolicy(attempts=0)


def test_retry_policy_invalid_backoff():
    with pytest.raises(ValueError, match="backoff"):
        RetryPolicy(backoff=-1.0)


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    """Replacement for time.sleep that does nothing in tests."""


def test_with_retry_succeeds_first_attempt():
    calls: list[int] = []

    def fn() -> str:
        calls.append(1)
        return "ok"

    result = with_retry(fn, RetryPolicy(attempts=3), _sleep=_no_sleep)
    assert result == "ok"
    assert len(calls) == 1


def test_with_retry_succeeds_on_second_attempt():
    calls: list[int] = []

    def fn() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("transient")
        return "ok"

    result = with_retry(fn, RetryPolicy(attempts=3, backoff=0.0), _sleep=_no_sleep)
    assert result == "ok"
    assert len(calls) == 2


def test_with_retry_raises_after_all_attempts_exhausted():
    def fn() -> str:
        raise TimeoutError("always fails")

    with pytest.raises(TimeoutError, match="always fails"):
        with_retry(fn, RetryPolicy(attempts=3, backoff=0.0), _sleep=_no_sleep)


def test_with_retry_sleep_called_between_attempts():
    slept: list[float] = []

    def fn() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        with_retry(
            fn,
            RetryPolicy(attempts=3, backoff=1.0),
            _sleep=slept.append,
        )

    assert len(slept) == 2
    assert slept[0] == 1.0
    assert slept[1] == 2.0


def test_with_retry_label_accepted():
    """Ensure *label* kwarg is accepted without error."""
    result = with_retry(
        lambda: 42,
        RetryPolicy(attempts=1),
        label="my-service",
        _sleep=_no_sleep,
    )
    assert result == 42
