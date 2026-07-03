"""THIN_SLICE: in-memory run persistence for the first run-lifecycle slice.

Replace with a bounded SQLite repository before dedicated-server readiness.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_RUNS: dict[str, dict[str, Any]] = {}
_HISTORY: dict[str, list[dict[str, Any]]] = {}


def reset_store() -> None:
    _RUNS.clear()
    _HISTORY.clear()


def save_run(record: dict[str, Any]) -> dict[str, Any]:
    stored = deepcopy(record)
    _RUNS[stored["run_id"]] = stored
    return deepcopy(stored)


def get_run(run_id: str) -> dict[str, Any] | None:
    record = _RUNS.get(run_id)
    return deepcopy(record) if record is not None else None


def list_runs() -> list[dict[str, Any]]:
    return [deepcopy(record) for record in _RUNS.values()]


def append_transition(history_ref: str, transition: dict[str, Any]) -> None:
    _HISTORY.setdefault(history_ref, []).append(deepcopy(transition))


def list_history(history_ref: str) -> list[dict[str, Any]]:
    return deepcopy(_HISTORY.get(history_ref, []))
