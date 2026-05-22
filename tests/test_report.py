"""Tests for stackping.report."""

from __future__ import annotations

from pathlib import Path

import pytest

from stackping.history import History, HistoryEntry
from stackping.report import ServiceSummary, format_report, summarise


@pytest.fixture()
def hist(tmp_path: Path) -> History:
    return History(path=tmp_path / "h.json")


def add_entry(hist: History, name: str, is_up: bool, code: int | None = None, error: str | None = None) -> None:
    hist.record(HistoryEntry.now(service_name=name, is_up=is_up, status_code=code, error=error))


def test_summarise_all_up(hist: History) -> None:
    for _ in range(5):
        add_entry(hist, "api", is_up=True, code=200)
    result = summarise(hist, ["api"])
    assert len(result) == 1
    s = result[0]
    assert s.total_checks == 5
    assert s.up_checks == 5
    assert s.uptime_pct == pytest.approx(100.0)
    assert "UP" in s.last_status


def test_summarise_partial_downtime(hist: History) -> None:
    for _ in range(3):
        add_entry(hist, "web", is_up=True, code=200)
    add_entry(hist, "web", is_up=False, code=503)
    result = summarise(hist, ["web"])
    s = result[0]
    assert s.up_checks == 3
    assert s.total_checks == 4
    assert s.uptime_pct == pytest.approx(75.0)
    assert "DOWN" in s.last_status
    assert "503" in s.last_status


def test_summarise_no_data(hist: History) -> None:
    result = summarise(hist, ["ghost"])
    s = result[0]
    assert s.total_checks == 0
    assert s.uptime_pct == 0.0
    assert s.last_status == "no data"


def test_summarise_down_with_error(hist: History) -> None:
    add_entry(hist, "db", is_up=False, code=None, error="timeout")
    result = summarise(hist, ["db"])
    assert "timeout" in result[0].last_status


def test_format_report_contains_header(hist: History) -> None:
    add_entry(hist, "svc", is_up=True, code=200)
    summaries = summarise(hist, ["svc"])
    report = format_report(summaries)
    assert "StackPing Uptime Report" in report
    assert "svc" in report


def test_format_report_empty() -> None:
    report = format_report([])
    assert "No services" in report


def test_service_summary_str() -> None:
    s = ServiceSummary(name="x", total_checks=10, up_checks=9, uptime_pct=90.0, last_status="UP (200)")
    text = str(s)
    assert "90.0%" in text
    assert "9/10" in text
    assert "UP (200)" in text
