"""Tests for stackping.checker."""

import pytest
import httpx
import respx

from stackping.checker import CheckResult, check_service
from stackping.config import Service


def make_service(
    name: str = "example",
    url: str = "https://example.com/health",
    expected_status: int = 200,
) -> Service:
    return Service(name=name, url=url, expected_status=expected_status, interval=60)


@respx.mock
def test_check_service_success():
    respx.get("https://example.com/health").mock(
        return_value=httpx.Response(200)
    )
    result = check_service(make_service())

    assert result.is_up is True
    assert result.status_code == 200
    assert result.error is None
    assert result.response_time_ms is not None
    assert result.response_time_ms >= 0


@respx.mock
def test_check_service_wrong_status():
    respx.get("https://example.com/health").mock(
        return_value=httpx.Response(503)
    )
    result = check_service(make_service())

    assert result.is_up is False
    assert result.status_code == 503
    assert "expected 200" in result.error


@respx.mock
def test_check_service_expected_non_200():
    svc = make_service(url="https://example.com/gone", expected_status=410)
    respx.get("https://example.com/gone").mock(
        return_value=httpx.Response(410)
    )
    result = check_service(svc)

    assert result.is_up is True
    assert result.status_code == 410


@respx.mock
def test_check_service_timeout():
    respx.get("https://example.com/health").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    result = check_service(make_service())

    assert result.is_up is False
    assert "timed out" in result.error
    assert result.status_code is None


@respx.mock
def test_check_service_connection_error():
    respx.get("https://example.com/health").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    result = check_service(make_service())

    assert result.is_up is False
    assert result.error is not None


def test_str_up():
    svc = make_service()
    result = CheckResult(service=svc, success=True, status_code=200, response_time_ms=42.5)
    assert "[UP]" in str(result)
    assert "example" in str(result)


def test_str_down():
    svc = make_service()
    result = CheckResult(service=svc, success=False, error="request timed out")
    assert "[DOWN]" in str(result)
    assert "timed out" in str(result)
