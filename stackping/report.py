"""Summarise check history for reporting and dashboard use."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from stackping.history import History


@dataclass
class ServiceSummary:
    name: str
    url: str
    total_checks: int
    up_checks: int
    uptime_pct: float
    last_status: Optional[bool]
    last_checked: Optional[datetime]

    def __str__(self) -> str:
        status = "UP" if self.last_status else ("DOWN" if self.last_status is False else "UNKNOWN")
        return (
            f"{self.name} ({self.url}): {status} "
            f"uptime={self.uptime_pct:.1f}% over {self.total_checks} checks"
        )


def summarise(history: History, service_name: str, window_hours: int = 24) -> ServiceSummary:
    """Return a ServiceSummary for *service_name* over the last *window_hours* hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    entries = [
        e for e in history.get(service_name)
        if e.timestamp >= cutoff
    ]

    total = len(entries)
    up_count = sum(1 for e in entries if e.up)
    uptime_pct = (up_count / total * 100.0) if total > 0 else 0.0

    last_entry = history.last(service_name)
    last_status: Optional[bool] = last_entry.up if last_entry else None
    last_checked: Optional[datetime] = last_entry.timestamp if last_entry else None
    url = last_entry.url if last_entry else ""

    return ServiceSummary(
        name=service_name,
        url=url,
        total_checks=total,
        up_checks=up_count,
        uptime_pct=uptime_pct,
        last_status=last_status,
        last_checked=last_checked,
    )


def format_report(history: History, service_names: List[str], window_hours: int = 24) -> str:
    """Format a plain-text report for all services."""
    lines: List[str] = [f"Uptime report (last {window_hours}h)", "=" * 40]
    for name in service_names:
        summary = summarise(history, name, window_hours=window_hours)
        lines.append(str(summary))
    return "\n".join(lines)
