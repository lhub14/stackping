"""Monitor loop: checks all services and dispatches notifications on state changes."""

from __future__ import annotations

import logging
import time
from typing import Dict

from stackping.checker import CheckResult, check_service
from stackping.config import Config, Service
from stackping.notifier import send_notification

logger = logging.getLogger(__name__)

# Track previous up/down state per service name to avoid duplicate alerts
_state: Dict[str, bool] = {}


def _should_notify(service: Service, result: CheckResult) -> bool:
    """Return True only when the service state has changed."""
    previous = _state.get(service.name)
    changed = previous is None or previous != result.is_up
    _state[service.name] = result.is_up
    return changed


def run_checks(config: Config) -> list[CheckResult]:
    """Check every service once and send webhook alerts on state changes."""
    results: list[CheckResult] = []
    for service in config.services:
        result = check_service(service)
        logger.info("%s", result)
        results.append(result)

        if service.webhook and _should_notify(service, result):
            notify_result = send_notification(service.webhook, result)
            logger.info("%s", notify_result)

    return results


def run_forever(config: Config) -> None:  # pragma: no cover
    """Continuously poll all services at their configured intervals."""
    logger.info("stackping started — monitoring %d service(s)", len(config.services))
    next_check: Dict[str, float] = {s.name: 0.0 for s in config.services}

    while True:
        now = time.monotonic()
        for service in config.services:
            if now >= next_check[service.name]:
                result = check_service(service)
                logger.info("%s", result)
                if service.webhook and _should_notify(service, result):
                    notify_result = send_notification(service.webhook, result)
                    logger.info("%s", notify_result)
                next_check[service.name] = time.monotonic() + service.interval
        time.sleep(1)
