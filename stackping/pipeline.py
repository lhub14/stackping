"""Pipeline: orchestrates check → alert for a single service."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from stackping.alertmanager import AlertManager
from stackping.checker import CheckResult, check_service
from stackping.config import Service
from stackping.history import History
from stackping.notifier import NotifyResult

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    service_name: str
    check: CheckResult
    notify: Optional[NotifyResult] = None

    @property
    def alerted(self) -> bool:
        return self.notify is not None


@dataclass
class Pipeline:
    """Runs the full check-and-alert pipeline for a list of services."""

    alert_manager: AlertManager = field(default_factory=AlertManager)
    history: Optional[History] = None

    def run_one(self, service: Service) -> PipelineResult:
        """Check a single service and send alert if warranted."""
        result = check_service(service)
        log.debug("%s check result: %s", service.name, result)

        if self.history is not None:
            from stackping.history import HistoryEntry, now
            self.history.record(HistoryEntry(
                service=service.name,
                timestamp=now(),
                up=result.up,
                latency_ms=result.latency_ms,
            ))

        notify: Optional[NotifyResult] = None
        if service.webhook:
            notify = self.alert_manager.maybe_send(service, result)

        return PipelineResult(service_name=service.name, check=result, notify=notify)

    def run_all(self, services: list[Service]) -> list[PipelineResult]:
        """Check all services and return results."""
        results = []
        for svc in services:
            try:
                results.append(self.run_one(svc))
            except Exception as exc:  # pragma: no cover
                log.error("Unexpected error checking %s: %s", svc.name, exc)
        return results
