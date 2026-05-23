"""Tests for stackping.healthcheck."""
from __future__ import annotations

import json
import socket
import time

import pytest
import urllib.request
import urllib.error

from stackping.healthcheck import HealthServer


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def server():
    port = _free_port()
    srv = HealthServer(host="127.0.0.1", port=port)
    srv.start()
    # Give the thread a moment to bind.
    time.sleep(0.05)
    yield srv
    srv.stop()


def _get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def test_health_returns_200(server: HealthServer) -> None:
    status, body = _get(f"http://127.0.0.1:{server.port}/health")
    assert status == 200


def test_health_default_payload(server: HealthServer) -> None:
    _, body = _get(f"http://127.0.0.1:{server.port}/health")
    data = json.loads(body)
    assert data == {"status": "starting"}


def test_health_updated_payload(server: HealthServer) -> None:
    server.update({"status": "ok", "checks": 42})
    _, body = _get(f"http://127.0.0.1:{server.port}/health")
    data = json.loads(body)
    assert data["status"] == "ok"
    assert data["checks"] == 42


def test_unknown_path_returns_404(server: HealthServer) -> None:
    status, _ = _get(f"http://127.0.0.1:{server.port}/unknown")
    assert status == 404


def test_stop_shuts_down_server(server: HealthServer) -> None:
    server.stop()
    # After stopping, the port should be unreachable.
    with pytest.raises(Exception):
        urllib.request.urlopen(
            f"http://127.0.0.1:{server.port}/health", timeout=1
        )
