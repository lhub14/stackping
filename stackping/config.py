"""Load and validate the YAML service configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class Service:
    name: str
    url: str
    interval: int = 60  # seconds between checks
    timeout: int = 10   # request timeout in seconds
    expected_status: int = 200
    tags: List[str] = field(default_factory=list)


@dataclass
class Config:
    services: List[Service]
    webhook_url: Optional[str] = None
    default_interval: int = 60
    default_timeout: int = 10


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""


def load_config(path: str | Path) -> Config:
    """Parse a YAML config file and return a Config instance."""
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r") as fh:
        try:
            raw = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping at the top level.")

    raw_services = raw.get("services")
    if not raw_services or not isinstance(raw_services, list):
        raise ConfigError("'services' key must be a non-empty list.")

    services: List[Service] = []
    for idx, svc in enumerate(raw_services):
        if not isinstance(svc, dict):
            raise ConfigError(f"Service at index {idx} must be a mapping.")
        if "name" not in svc:
            raise ConfigError(f"Service at index {idx} is missing 'name'.")
        if "url" not in svc:
            raise ConfigError(f"Service at index {idx} is missing 'url'.")
        services.append(
            Service(
                name=svc["name"],
                url=svc["url"],
                interval=svc.get("interval", raw.get("default_interval", 60)),
                timeout=svc.get("timeout", raw.get("default_timeout", 10)),
                expected_status=svc.get("expected_status", 200),
                tags=svc.get("tags", []),
            )
        )

    return Config(
        services=services,
        webhook_url=raw.get("webhook_url"),
        default_interval=raw.get("default_interval", 60),
        default_timeout=raw.get("default_timeout", 10),
    )
