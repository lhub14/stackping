"""Tests for stackping.dashboard."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from stackping.dashboard import DashboardRow, build_rows, render_dashboard
from stackping.report import ServiceSummary


def make_summary(
    name="api",
    url="https://example.com",
    total_checks=10,
    up_checks=10,
    uptime_pct=100.0,
    last_status=True,
    last_checked=None,
) -> ServiceSummary:
    return ServiceSummary(
        name=name,
        url=url,
        total_checks=total_checks,
        up_checks=up_checks,
        uptime_pct=uptime_pct,
        last_status=last_status,
        last_checked=last_checked or datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_dashboard_row_str_up():
    row = DashboardRow(
        name="api",
        url="https://example.com",
        status="up",
        uptime_pct=99.5,
        last_checked=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    text = str(row)
    assert "api" in text
    assert "99.5%" in text
    assert "2024-06-01" in text


def test_dashboard_row_str_unknown_no_data():
    row = DashboardRow(
        name="db", url="https://db.example.com",
        status="unknown", uptime_pct=None, last_checked=None,
    )
    text = str(row)
    assert "n/a" in text
    assert "never" in text


def test_build_rows_up():
    summaries = [make_summary(name="svc", last_status=True, uptime_pct=100.0)]
    rows = build_rows(summaries)
    assert len(rows) == 1
    assert rows[0].status == "up"
    assert rows[0].uptime_pct == 100.0


def test_build_rows_down():
    summaries = [make_summary(name="svc", last_status=False, up_checks=5, uptime_pct=50.0)]
    rows = build_rows(summaries)
    assert rows[0].status == "down"


def test_build_rows_no_data():
    summaries = [make_summary(name="svc", total_checks=0, up_checks=0, uptime_pct=0.0, last_status=None)]
    rows = build_rows(summaries)
    assert rows[0].status == "unknown"
    assert rows[0].uptime_pct is None


def test_render_dashboard_contains_header_and_services(tmp_path):
    from stackping.history import History
    from stackping.checker import CheckResult

    hist = History(tmp_path / "h.json")
    hist.record("api", "https://api.example.com", CheckResult(up=True, status_code=200, latency_ms=42.0))
    hist.record("db", "https://db.example.com", CheckResult(up=False, status_code=500, latency_ms=10.0))

    output = render_dashboard(hist, ["api", "db"], window_hours=24)
    assert "stackping dashboard" in output
    assert "api" in output
    assert "db" in output
    assert "window=24h" in output
