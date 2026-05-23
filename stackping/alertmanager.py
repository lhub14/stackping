"""Alert manager: combines throttle + retry + notifier into a single call."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict

from stackping.checker import CheckResult
from stackping.config import Service
from stackping.notifier import NotifyResult, send_notification
from stackping.retry import RetryPolicy, with_retry
from stackping.throttle import Throttle, ThrottlePolicy

log = logging.getLogger(__name__)

_DEFAULT_RETRY = RetryPolicy(attempts=3, backoff=2.0, max_backoff=30.0)
_DEFAULT_THROTTLE = ThrottlePolicy(min_interval_seconds=300)


@dataclass
class AlertManager:
    """Stateful manager that gates and delivers notifications."""

    retry_policy: RetryPolicy = field(default_factory=lambda: _DEFAULT_RETRY)
    throttle_policy: ThrottlePolicy = field(default_factory=lambda: _DEFAULT_THROTTLE)
    _throttles: Dict[str, Throttle] = field(default_factory=dict, init=False, repr=False)

    def _throttle_for(self, service: Service) -> Throttle:
        key = service.name
        if key not in self._throttles:
            self._throttles[key] = Throttle(self.throttle_policy)
        return self._throttles[key]

    def maybe_send(self, service: Service, result: CheckResult) -> NotifyResult | None:
        """Send a notification if throttle allows; returns result or None if suppressed."""
        throttle = self._throttle_for(service)
        if not throttle.should_alert():
            log.debug("Alert suppressed for %s (throttled)", service.name)
            return None

        def _attempt() -> NotifyResult:
            return send_notification(service, result)

        notify_result = with_retry(_attempt, self.retry_policy)
        if notify_result.ok:
            throttle.record_alert()
            log.info("Alert sent for %s", service.name)
        else:
            log.warning("Alert failed for %s: %s", service.name, notify_result.error)
        return notify_result

    def reset(self, service_name: str) -> None:
        """Clear throttle state for a service (e.g. after it recovers)."""
        self._throttles.pop(service_name, None)
