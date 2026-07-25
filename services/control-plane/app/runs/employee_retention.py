"""Bounded retention for terminal role-tagged worker run history."""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store

logger = logging.getLogger(__name__)

DEFAULT_KEEP_PER_ROLE = 8
DEFAULT_MAX_DELETES_PER_TICK = 50
# Startup / manual drain may clear a larger backlog than one scheduler tick.
DEFAULT_MAX_DELETES_PER_DRAIN = 500
DEFAULT_MAX_DRAIN_ROUNDS = 20


def employee_run_retention_per_role() -> int:
    raw = os.environ.get("AXON_WATCH_EMPLOYEE_RUN_RETENTION_PER_ROLE", "").strip()
    if not raw:
        return DEFAULT_KEEP_PER_ROLE
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_KEEP_PER_ROLE
    return max(1, value)


def _retention_sort_key(record: dict[str, Any]) -> tuple[str, str]:
    stamp = ""
    for field in ("ended_at", "updated_at", "started_at"):
        stamp = str(record.get(field) or "").strip()
        if stamp:
            break
    return stamp, str(record.get("run_id") or "")


def prune_terminal_employee_runs(
    *,
    keep_per_role: int | None = None,
    max_deletes: int | None = None,
) -> list[str]:
    """Delete oldest terminal employee runs beyond the per-role retention window.

    Only role-tagged runs in terminal phases are eligible. Operator-initiated runs
    and in-flight employee shifts are never deleted here.
    """
    keep = (
        employee_run_retention_per_role()
        if keep_per_role is None
        else max(0, int(keep_per_role))
    )
    delete_budget = (
        DEFAULT_MAX_DELETES_PER_TICK
        if max_deletes is None
        else max(0, int(max_deletes))
    )
    if delete_budget == 0:
        return []

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in run_store.list_runs():
        role = str(record.get("employee_role") or "").strip().lower()
        if not role:
            continue
        phase = str(record.get("phase") or "").strip()
        if not is_terminal_phase(phase):
            continue
        workspace_id = str(record.get("workspace_id") or "").strip()
        grouped[(workspace_id, role)].append(record)

    candidates: list[tuple[tuple[str, str], str]] = []
    for records in grouped.values():
        records.sort(key=_retention_sort_key, reverse=True)
        for stale in records[keep:]:
            run_id = str(stale.get("run_id") or "").strip()
            if run_id:
                candidates.append((_retention_sort_key(stale), run_id))

    candidates.sort()
    pruned: list[str] = []
    for _, run_id in candidates[:delete_budget]:
        if run_store.delete_run(run_id):
            pruned.append(run_id)
            logger.info("pruned terminal employee run %s", run_id)
    return pruned


def drain_terminal_employee_runs(
    *,
    keep_per_role: int | None = None,
    max_deletes_per_round: int | None = None,
    max_rounds: int | None = None,
) -> list[str]:
    """Prune repeatedly until the retention window is satisfied or rounds end.

    Use on control-plane startup and the manual prune API so a large terminal
    history backlog clears in one pass. Scheduler ticks keep using the smaller
    per-tick budget so continuous shifts stay responsive.
    """
    rounds = (
        DEFAULT_MAX_DRAIN_ROUNDS
        if max_rounds is None
        else max(0, int(max_rounds))
    )
    per_round = (
        DEFAULT_MAX_DELETES_PER_DRAIN
        if max_deletes_per_round is None
        else max(0, int(max_deletes_per_round))
    )
    drained: list[str] = []
    for _ in range(rounds):
        batch = prune_terminal_employee_runs(
            keep_per_role=keep_per_role,
            max_deletes=per_round,
        )
        if not batch:
            break
        drained.extend(batch)
        if len(batch) < per_round:
            break
    return drained


__all__ = [
    "DEFAULT_KEEP_PER_ROLE",
    "DEFAULT_MAX_DELETES_PER_DRAIN",
    "DEFAULT_MAX_DELETES_PER_TICK",
    "DEFAULT_MAX_DRAIN_ROUNDS",
    "drain_terminal_employee_runs",
    "employee_run_retention_per_role",
    "prune_terminal_employee_runs",
]
