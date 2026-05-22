"""Generate a plain-text uptime summary report from history data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from stackping.history import History, HistoryEntry


@dataclass
class ServiceSummary:
    name: str
    total_checks: int
    up_checks: int
    uptime_pct: float
    last_status: str

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.uptime_pct:.1f}% uptime "
            f"({self.up_checks}/{self.total_checks} checks) — last: {self.last_status}"
        )


def summarise(history: History, service_names: Sequence[str]) -> list[ServiceSummary]:
    """Return a summary for each service name."""
    summaries: list[ServiceSummary] = []
    for name in service_names:
        entries: list[HistoryEntry] = history.get(name)
        total = len(entries)
        if total == 0:
            summaries.append(ServiceSummary(name=name, total_checks=0, up_checks=0,
                                            uptime_pct=0.0, last_status="no data"))
            continue
        up_count = sum(1 for e in entries if e.is_up)
        pct = (up_count / total) * 100.0
        last = entries[-1]
        if last.is_up:
            last_status = f"UP ({last.status_code})"
        else:
            detail = last.error or str(last.status_code)
            last_status = f"DOWN ({detail})"
        summaries.append(ServiceSummary(name=name, total_checks=total, up_checks=up_count,
                                        uptime_pct=pct, last_status=last_status))
    return summaries


def format_report(summaries: list[ServiceSummary]) -> str:
    """Render summaries as a human-readable string."""
    if not summaries:
        return "No services tracked yet."
    lines = ["=== StackPing Uptime Report ==="]
    for s in summaries:
        lines.append(f"  {s}")
    lines.append(f"  Total services: {len(summaries)}")
    return "\n".join(lines)
