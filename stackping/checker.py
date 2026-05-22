"""HTTP health checker for monitored services."""

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from stackping.config import Service


@dataclass
class CheckResult:
    """Result of a single health check."""

    service: Service
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def is_up(self) -> bool:
        return self.success

    def __str__(self) -> str:
        if self.success:
            return (
                f"[UP] {self.service.name} "
                f"({self.status_code}, {self.response_time_ms:.1f}ms)"
            )
        return f"[DOWN] {self.service.name} — {self.error or self.status_code}"


def check_service(
    service: Service,
    timeout: float = 10.0,
) -> CheckResult:
    """Perform an HTTP GET against *service* and return a CheckResult."""
    start = time.monotonic()
    try:
        response = httpx.get(
            service.url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "stackping/1.0"},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        success = response.status_code == service.expected_status
        return CheckResult(
            service=service,
            success=success,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            error=None
            if success
            else f"expected {service.expected_status}, got {response.status_code}",
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            service=service,
            success=False,
            response_time_ms=elapsed_ms,
            error="request timed out",
        )
    except httpx.RequestError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            service=service,
            success=False,
            response_time_ms=elapsed_ms,
            error=str(exc),
        )
