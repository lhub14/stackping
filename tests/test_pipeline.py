"""Tests for stackping.pipeline."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stackping.checker import CheckResult
from stackping.config import Service
from stackping.notifier import NotifyResult
from stackping.pipeline import Pipeline, PipelineResult


def make_service(name="api", webhook="http://hook") -> Service:
    return Service(name=name, url="http://example.com", webhook=webhook, interval=30)


def make_check(up: bool = True) -> CheckResult:
    return CheckResult(up=up, status_code=200 if up else 503, latency_ms=10.0)


@pytest.fixture
def pipeline():
    return Pipeline()


def test_run_one_up_service_no_webhook(pipeline):
    svc = make_service(webhook="")
    check = make_check(up=True)
    with patch("stackping.pipeline.check_service", return_value=check):
        result = pipeline.run_one(svc)
    assert result.check.up is True
    assert result.notify is None
    assert not result.alerted


def test_run_one_sends_alert_when_webhook_set(pipeline):
    svc = make_service()
    check = make_check(up=False)
    notify = NotifyResult(ok=True)
    with patch("stackping.pipeline.check_service", return_value=check), \
         patch.object(pipeline.alert_manager, "maybe_send", return_value=notify) as mock_send:
        result = pipeline.run_one(svc)
    mock_send.assert_called_once_with(svc, check)
    assert result.alerted is True
    assert result.notify.ok is True


def test_run_one_records_to_history(pipeline, tmp_path):
    from stackping.history import History
    hist = History(tmp_path / "h.json")
    pipeline.history = hist
    svc = make_service()
    check = make_check()
    with patch("stackping.pipeline.check_service", return_value=check), \
         patch.object(pipeline.alert_manager, "maybe_send", return_value=NotifyResult(ok=True)):
        pipeline.run_one(svc)
    entries = hist.get(svc.name)
    assert len(entries) == 1
    assert entries[0].up is True


def test_run_all_returns_all_results(pipeline):
    services = [make_service(name="a"), make_service(name="b")]
    check = make_check()
    notify = NotifyResult(ok=True)
    with patch("stackping.pipeline.check_service", return_value=check), \
         patch.object(pipeline.alert_manager, "maybe_send", return_value=notify):
        results = pipeline.run_all(services)
    assert len(results) == 2
    assert {r.service_name for r in results} == {"a", "b"}


def test_pipeline_result_alerted_false_when_no_notify():
    check = make_check()
    pr = PipelineResult(service_name="x", check=check, notify=None)
    assert pr.alerted is False


def test_pipeline_result_alerted_true_when_notify_present():
    check = make_check()
    pr = PipelineResult(service_name="x", check=check, notify=NotifyResult(ok=True))
    assert pr.alerted is True
