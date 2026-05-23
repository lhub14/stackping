"""Simple text-based status dashboard rendered to stdout."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from stackping.history import History
from stackping.report import ServiceSummary, summarise

_UP = "\033[32m●\033[0m"
_DOWN = "\033[31m●\033[0m"
_UNKNOWN = "\033[33m●\033[0m"


@dataclass
class DashboardRow:
    name: str
    url: str
    status: str          # "up", "down", "unknown"
    uptime_pct: float | None
    last_checked: datetime | None

    def __str__(self) -> str:
        indicator = {"up": _UP, "down": _DOWN}.get(self.status, _UNKNOWN)
        uptime = f"{self.uptime_pct:.1f}%" if self.uptime_pct is not None else "n/a"
        if self.last_checked:
            ts = self.last_checked.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts = "never"
        return f"{indicator}  {self.name:<30} {self.url:<45} uptime={uptime:<8} last={ts}"


def build_rows(summaries: List[ServiceSummary]) -> List[DashboardRow]:
    """Convert a list of ServiceSummary objects into DashboardRow objects."""
    rows: List[DashboardRow] = []
    for s in summaries:
        if s.total_checks == 0:
            status = "unknown"
        elif s.last_status is True:
            status = "up"
        else:
            status = "down"
        rows.append(
            DashboardRow(
                name=s.name,
                url=s.url,
                status=status,
                uptime_pct=s.uptime_pct if s.total_checks > 0 else None,
                last_checked=s.last_checked,
            )
        )
    return rows


def render_dashboard(history: History, service_names: List[str], window_hours: int = 24) -> str:
    """Render a full dashboard string for the given services."""
    summaries = [summarise(history, name, window_hours=window_hours) for name in service_names]
    rows = build_rows(summaries)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = f"stackping dashboard — {now_str}  (window={window_hours}h)"
    separator = "─" * 100
    lines = [header, separator] + [str(r) for r in rows] + [separator]
    return "\n".join(lines)
