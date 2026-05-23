"""HTTP health-check endpoint so orchestrators can probe stackping itself."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

_GetStatus = Callable[[], dict]


class _Handler(BaseHTTPRequestHandler):
    """Minimal request handler that serves /health and /metrics."""

    get_status: _GetStatus  # injected by HealthServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            payload = self.get_status()
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        """Suppress default stderr logging."""


class HealthServer:
    """Tiny HTTP server that exposes a /health endpoint in a daemon thread."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self._status: dict = {"status": "starting"}
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, status: dict) -> None:
        """Replace the current status payload (thread-safe)."""
        self._status = status

    def start(self) -> None:
        """Start the HTTP server in a background daemon thread."""
        handler = _Handler
        handler.get_status = lambda: self._status  # type: ignore[method-assign]

        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="healthcheck-server",
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the server gracefully."""
        if self._server is not None:
            self._server.shutdown()
