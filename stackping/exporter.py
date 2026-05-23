"""Prometheus-style metrics exporter for stackping."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from stackping.report import ServiceSummary


@dataclass
class MetricLine:
    name: str
    labels: dict[str, str]
    value: float

    def __str__(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(self.labels.items()))
        if label_str:
            return f"{self.name}{{{label_str}}} {self.value}"
        return f"{self.name} {self.value}"


def build_metrics(summaries: Iterable[ServiceSummary]) -> list[MetricLine]:
    """Convert service summaries into a flat list of metric lines."""
    lines: list[MetricLine] = []
    for s in summaries:
        labels = {"service": s.name}
        lines.append(
            MetricLine(
                name="stackping_uptime_ratio",
                labels=labels,
                value=round(s.uptime_ratio, 6) if s.uptime_ratio is not None else -1.0,
            )
        )
        lines.append(
            MetricLine(
                name="stackping_total_checks",
                labels=labels,
                value=float(s.total_checks),
            )
        )
        lines.append(
            MetricLine(
                name="stackping_up_checks",
                labels=labels,
                value=float(s.up_checks),
            )
        )
    return lines


def render_metrics(summaries: Iterable[ServiceSummary]) -> str:
    """Render metrics in a Prometheus exposition-compatible text format."""
    lines = build_metrics(summaries)
    if not lines:
        return ""
    header_lines = [
        "# HELP stackping_uptime_ratio Fraction of checks that were UP (-1 if no data)",
        "# TYPE stackping_uptime_ratio gauge",
        "# HELP stackping_total_checks Total number of checks performed",
        "# TYPE stackping_total_checks counter",
        "# HELP stackping_up_checks Number of checks that returned UP",
        "# TYPE stackping_up_checks counter",
    ]
    metric_lines = [str(l) for l in lines]
    return "\n".join(header_lines + metric_lines) + "\n"
