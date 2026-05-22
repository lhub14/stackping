"""Webhook notifier for sending alerts when services go down or recover."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from stackping.checker import CheckResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


@dataclass
class NotifyResult:
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return f"Notification sent (HTTP {self.status_code})"
        return f"Notification failed: {self.error}"


def build_payload(result: CheckResult) -> dict:
    """Build the webhook JSON payload from a CheckResult."""
    status = "DOWN" if not result.is_up else "UP"
    payload = {
        "service": result.service.name,
        "url": result.service.url,
        "status": status,
        "latency_ms": round(result.latency_ms, 2) if result.latency_ms is not None else None,
        "error": result.error,
    }
    if result.status_code is not None:
        payload["http_status"] = result.status_code
    return payload


def send_notification(webhook_url: str, result: CheckResult, timeout: int = DEFAULT_TIMEOUT) -> NotifyResult:
    """POST a JSON payload to the configured webhook URL."""
    payload = build_payload(result)
    try:
        response = requests.post(webhook_url, json=payload, timeout=timeout)
        response.raise_for_status()
        logger.info("Webhook delivered for '%s': HTTP %s", result.service.name, response.status_code)
        return NotifyResult(success=True, status_code=response.status_code)
    except requests.exceptions.RequestException as exc:
        logger.error("Webhook delivery failed for '%s': %s", result.service.name, exc)
        return NotifyResult(success=False, error=str(exc))
