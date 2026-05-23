"""Alert throttling: suppress repeated notifications for the same service."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottlePolicy:
    """Controls how often alerts may be re-sent for a given service."""

    # Minimum seconds between repeated alerts for the same service+state.
    min_interval: float = 300.0  # 5 minutes default

    def __post_init__(self) -> None:
        if self.min_interval < 0:
            raise ValueError("min_interval must be >= 0")


@dataclass
class Throttle:
    """Stateful throttle that tracks when each service was last alerted."""

    policy: ThrottlePolicy = field(default_factory=ThrottlePolicy)
    # Maps service_name -> (state, timestamp)
    _last_alert: Dict[str, tuple[str, float]] = field(
        default_factory=dict, init=False, repr=False
    )

    def should_alert(self, service_name: str, state: str) -> bool:
        """Return True if an alert should be sent for *service_name* in *state*.

        An alert is allowed when:
        - The service has never been alerted before, OR
        - The state has changed since the last alert, OR
        - Enough time has passed since the last alert for the same state.
        """
        now = time.monotonic()
        if service_name not in self._last_alert:
            return True
        last_state, last_ts = self._last_alert[service_name]
        if last_state != state:
            return True
        return (now - last_ts) >= self.policy.min_interval

    def record_alert(self, service_name: str, state: str) -> None:
        """Record that an alert was just sent for *service_name* in *state*."""
        self._last_alert[service_name] = (state, time.monotonic())

    def reset(self, service_name: Optional[str] = None) -> None:
        """Clear throttle state for one service or all services."""
        if service_name is None:
            self._last_alert.clear()
        else:
            self._last_alert.pop(service_name, None)

    def time_until_next_alert(self, service_name: str) -> Optional[float]:
        """Return seconds remaining before *service_name* may be alerted again.

        Returns ``None`` if the service has no recorded alert or if an alert
        is already allowed (i.e. the wait period has elapsed).  Returns a
        positive float representing the remaining cooldown otherwise.
        """
        if service_name not in self._last_alert:
            return None
        _state, last_ts = self._last_alert[service_name]
        remaining = self.policy.min_interval - (time.monotonic() - last_ts)
        return remaining if remaining > 0 else None
