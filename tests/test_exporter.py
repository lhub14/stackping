"""Tests for stackping.exporter."""
from __future__ import annotations

import pytest

from stackping.exporter import MetricLine, build_metrics, render_metrics
from stackping.report import ServiceSummary


def make_summary(
    name: str,
    total: int = 10,
    up: int = 10,
    uptime: float | None = 1.0,
) -> ServiceSummary:
    return ServiceSummary(name=name, total_checks=total, up_checks=up, uptime_ratio=uptime)


# ---------------------------------------------------------------------------
# MetricLine
# ---------------------------------------------------------------------------

def test_metric_line_str_with_labels():
    m = MetricLine(name="stackping_uptime_ratio", labels={"service": "api"}, value=0.99)
    assert str(m) == 'stackping_uptime_ratio{service="api"} 0.99'


def test_metric_line_str_no_labels():
    m = MetricLine(name="stackping_total_checks", labels={}, value=42.0)
    assert str(m) == "stackping_total_checks 42.0"


def test_metric_line_labels_sorted():
    m = MetricLine(name="x", labels={"z": "1", "a": "2"}, value=0.0)
    assert str(m).startswith('x{a="2",z="1"}')


# ---------------------------------------------------------------------------
# build_metrics
# ---------------------------------------------------------------------------

def test_build_metrics_returns_three_lines_per_service():
    summaries = [make_summary("web"), make_summary("db")]
    lines = build_metrics(summaries)
    assert len(lines) == 6


def test_build_metrics_uptime_ratio_value():
    s = make_summary("api", total=4, up=3, uptime=0.75)
    lines = build_metrics([s])
    ratio_line = next(l for l in lines if l.name == "stackping_uptime_ratio")
    assert ratio_line.value == pytest.approx(0.75)


def test_build_metrics_no_data_uptime_is_minus_one():
    s = make_summary("api", total=0, up=0, uptime=None)
    lines = build_metrics([s])
    ratio_line = next(l for l in lines if l.name == "stackping_uptime_ratio")
    assert ratio_line.value == -1.0


def test_build_metrics_empty_input():
    assert build_metrics([]) == []


# ---------------------------------------------------------------------------
# render_metrics
# ---------------------------------------------------------------------------

def test_render_metrics_contains_help_lines():
    output = render_metrics([make_summary("svc")])
    assert "# HELP stackping_uptime_ratio" in output
    assert "# TYPE stackping_uptime_ratio gauge" in output


def test_render_metrics_contains_service_label():
    output = render_metrics([make_summary("my-service")])
    assert 'service="my-service"' in output


def test_render_metrics_ends_with_newline():
    output = render_metrics([make_summary("svc")])
    assert output.endswith("\n")


def test_render_metrics_empty_returns_empty_string():
    assert render_metrics([]) == ""


def test_render_metrics_multiple_services():
    summaries = [make_summary("a"), make_summary("b")]
    output = render_metrics(summaries)
    assert 'service="a"' in output
    assert 'service="b"' in output
