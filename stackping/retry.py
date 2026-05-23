"""Retry logic for HTTP checks with configurable backoff."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Defines how many times and how long to retry a failing check."""

    attempts: int = 3
    backoff: float = 2.0  # seconds between attempts (doubles each retry)
    max_backoff: float = 30.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be >= 1")
        if self.backoff < 0:
            raise ValueError("backoff must be >= 0")

    def delays(self) -> list[float]:
        """Return the sequence of delays (seconds) between retry attempts."""
        result: list[float] = []
        delay = self.backoff
        for _ in range(self.attempts - 1):
            result.append(min(delay, self.max_backoff))
            delay *= 2
        return result


def with_retry(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    label: str = "",
    _sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call *fn* up to *policy.attempts* times, sleeping between failures.

    Returns the first successful result.  If every attempt raises, the
    last exception is re-raised.
    """
    delays = policy.delays()
    last_exc: Exception | None = None

    for attempt in range(1, policy.attempts + 1):
        try:
            result = fn()
            if attempt > 1:
                logger.debug("%s succeeded on attempt %d", label or "call", attempt)
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "%s attempt %d/%d failed: %s",
                label or "call",
                attempt,
                policy.attempts,
                exc,
            )
            if attempt <= len(delays):
                _sleep(delays[attempt - 1])

    raise last_exc  # type: ignore[misc]
