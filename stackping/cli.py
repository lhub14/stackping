"""Command-line interface for stackping."""

import argparse
import logging
import sys
from pathlib import Path

from stackping.config import ConfigError, load_config
from stackping.monitor import run_forever

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stackping",
        description="Lightweight uptime monitor that reads a YAML service list and sends alerts via webhook.",
    )
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to the YAML services configuration file.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run checks once and exit instead of looping forever.",
    )
    return parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=getattr(logging, level),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.log_level)

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Configuration file not found: %s", config_path)
        return 1

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        logger.error("Failed to load configuration: %s", exc)
        return 1

    logger.info(
        "Loaded %d service(s) from %s", len(config.services), config_path
    )

    try:
        run_forever(config, run_once=args.once)
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
