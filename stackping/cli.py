"""Command-line interface for stackping."""
from __future__ import annotations

import logging
import signal
import sys
from argparse import ArgumentParser, Namespace
from typing import Optional

from stackping.config import ConfigError, load_config
from stackping.healthcheck import HealthServer
from stackping.monitor import run_checks, run_forever

log = logging.getLogger(__name__)

_DEFAULT_LOG_LEVEL = "INFO"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="stackping",
        description="Lightweight uptime monitor",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="services.yaml",
        help="Path to YAML service config (default: services.yaml)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check pass then exit",
    )
    parser.add_argument(
        "--log-level",
        default=_DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--health-port",
        type=int,
        default=None,
        metavar="PORT",
        help="Expose /health HTTP endpoint on PORT (disabled by default)",
    )
    return parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=getattr(logging, level),
    )


def _start_health_server(port: int) -> HealthServer:
    srv = HealthServer(port=port)
    srv.start()
    log.info("Health endpoint listening on http://0.0.0.0:%d/health", port)
    return srv


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args: Namespace = parser.parse_args(argv)
    setup_logging(args.log_level)

    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        log.error("Failed to load config: %s", exc)
        return 1

    health_server: Optional[HealthServer] = None
    if args.health_port is not None:
        health_server = _start_health_server(args.health_port)
        health_server.update({"status": "ok", "services": len(config.services)})

    def _shutdown(sig: int, _frame: object) -> None:  # pragma: no cover
        log.info("Received signal %d, shutting down.", sig)
        if health_server:
            health_server.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)

    if args.once:
        run_checks(config)
        return 0

    run_forever(config)  # pragma: no cover
    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
