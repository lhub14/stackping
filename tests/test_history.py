"""Tests for stackping.history."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stackping.history import History, HistoryEntry, MAX_ENTRIES_PER_SERVICE


@pytest.fixture()
def hist_file(tmp_path: Path) -> Path:
    return tmp_path / "history.json"


@pytest.fixture()
def hist(hist_file: Path) -> History:
    return History(path=hist_file)


def make_entry(name: str = "svc", is_up: bool = True, code: int | None = 200, error: str | None = None) -> HistoryEntry:
    return HistoryEntry.now(service_name=name, is_up=is_up, status_code=code, error=error)


def test_record_and_retrieve(hist: History) -> None:
    entry = make_entry()
    hist.record(entry)
    entries = hist.get("svc")
    assert len(entries) == 1
    assert entries[0].service_name == "svc"
    assert entries[0].is_up is True
    assert entries[0].status_code == 200


def test_last_returns_most_recent(hist: History) -> None:
    hist.record(make_entry(is_up=True))
    hist.record(make_entry(is_up=False, code=503))
    last = hist.last("svc")
    assert last is not None
    assert last.is_up is False
    assert last.status_code == 503


def test_last_returns_none_when_empty(hist: History) -> None:
    assert hist.last("nonexistent") is None


def test_persists_to_disk(hist_file: Path) -> None:
    h = History(path=hist_file)
    h.record(make_entry(name="alpha"))
    h2 = History(path=hist_file)
    assert len(h2.get("alpha")) == 1


def test_cap_at_max_entries(hist: History) -> None:
    for _ in range(MAX_ENTRIES_PER_SERVICE + 20):
        hist.record(make_entry())
    assert len(hist.get("svc")) == MAX_ENTRIES_PER_SERVICE


def test_clear_single_service(hist: History) -> None:
    hist.record(make_entry(name="a"))
    hist.record(make_entry(name="b"))
    hist.clear("a")
    assert hist.get("a") == []
    assert len(hist.get("b")) == 1


def test_clear_all(hist: History) -> None:
    hist.record(make_entry(name="a"))
    hist.record(make_entry(name="b"))
    hist.clear()
    assert hist.get("a") == []
    assert hist.get("b") == []


def test_corrupted_file_falls_back_to_empty(hist_file: Path) -> None:
    hist_file.write_text("not valid json")
    h = History(path=hist_file)
    assert h.get("anything") == []


def test_entry_error_field(hist: History) -> None:
    entry = make_entry(is_up=False, code=None, error="Connection refused")
    hist.record(entry)
    retrieved = hist.last("svc")
    assert retrieved is not None
    assert retrieved.error == "Connection refused"
    assert retrieved.status_code is None
