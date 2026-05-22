"""Persistent check history using a simple JSON file store."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

DEFAULT_HISTORY_FILE = Path("stackping_history.json")
MAX_ENTRIES_PER_SERVICE = 100


@dataclass
class HistoryEntry:
    service_name: str
    timestamp: str
    is_up: bool
    status_code: Optional[int]
    error: Optional[str]

    @staticmethod
    def now(service_name: str, is_up: bool, status_code: Optional[int], error: Optional[str]) -> "HistoryEntry":
        ts = datetime.now(timezone.utc).isoformat()
        return HistoryEntry(service_name=service_name, timestamp=ts, is_up=is_up,
                            status_code=status_code, error=error)


class History:
    """Read/write check history from a JSON file."""

    def __init__(self, path: Path = DEFAULT_HISTORY_FILE) -> None:
        self._path = path
        self._data: dict[str, list[dict]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open() as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Could not load history file %s: %s", self._path, exc)
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        try:
            with self._path.open("w") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError as exc:
            log.error("Could not save history file %s: %s", self._path, exc)

    def record(self, entry: HistoryEntry) -> None:
        bucket = self._data.setdefault(entry.service_name, [])
        bucket.append(asdict(entry))
        if len(bucket) > MAX_ENTRIES_PER_SERVICE:
            self._data[entry.service_name] = bucket[-MAX_ENTRIES_PER_SERVICE:]
        self._save()

    def get(self, service_name: str) -> list[HistoryEntry]:
        raw = self._data.get(service_name, [])
        return [HistoryEntry(**r) for r in raw]

    def last(self, service_name: str) -> Optional[HistoryEntry]:
        entries = self.get(service_name)
        return entries[-1] if entries else None

    def clear(self, service_name: Optional[str] = None) -> None:
        if service_name:
            self._data.pop(service_name, None)
        else:
            self._data = {}
        self._save()
