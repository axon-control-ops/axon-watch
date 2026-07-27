"""Explicit scheduled work sources for company-like autonomous starts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import task_store
from app.runs.service import list_runs

logger = logging.getLogger(__name__)

CONFIG_REL = Path("config/autonomy-work-sources.json")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_work_source_config(root: Path | None = None) -> dict[str, Any]:
    repo = root or _repo_root()
    path = repo / CONFIG_REL
    if not path.is_file():
        return {"schema_version": 1, "defaults": {"enabled": True}, "sources": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("autonomy work-source config unreadable: %s", exc)
        return {"schema_version": 1, "defaults": {"enabled": False}, "sources": []}


def list_enabled_work_sources(root: Path | None = None) -> list[dict[str, Any]]:
    config = load_work_source_config(root)
    if not bool((config.get("defaults") or {}).get("enabled", True)):
        return []
    sources: list[dict[str, Any]] = []
    for raw in config.get("sources") or []:
        if not isinstance(raw, dict):
            continue
        if not bool(raw.get("enabled", True)):
            continue
        source_id = str(raw.get("id") or "").strip()
        if not source_id:
            continue
        sources.append(raw)
    return sources


def recover_orphaned_remediation_leases() -> list[dict[str, Any]]:
    """Reopen leased tasks whose bound runs are already terminal."""
    terminal_ids = [
        str(record.get("run_id") or "").strip()
        for record in list_runs()
        if is_terminal_phase(str(record.get("phase") or ""))
        and str(record.get("run_id") or "").strip()
    ]
    recovered = task_store.reopen_orphaned_leased_tasks(
        terminal_run_ids=terminal_ids,
        terminal_outcome="run terminal; scheduler recovered lease",
    )
    if recovered:
        logger.info(
            "company work sources recovered %s orphaned leased task(s)",
            len(recovered),
        )
    return recovered


def run_scheduled_work_sources(*, root: Path | None = None) -> dict[str, Any]:
    """Tick every explicit company work source that is scheduler-driven."""
    results: dict[str, Any] = {
        "recovered_leases": recover_orphaned_remediation_leases(),
        "sources": {},
    }
    for source in list_enabled_work_sources(root):
        source_id = str(source.get("id") or "").strip()
        trigger = str(source.get("trigger") or "").strip().lower()
        if source_id == "file_size_patrol" and "scheduler" in trigger:
            from app.workspace_agents.file_size_patrol import run_file_size_patrol

            workspace_id = (
                str(source.get("workspace_id") or "workspace_axon_watch").strip()
                or "workspace_axon_watch"
            )
            owner_role = str(source.get("owner_role") or "watcher").strip() or "watcher"
            max_new = int(source.get("max_new_tasks_per_tick") or 1)
            try:
                results["sources"][source_id] = run_file_size_patrol(
                    workspace_id=workspace_id,
                    owner_role=owner_role,
                    max_new_tasks=max_new,
                    root=root,
                )
            except Exception:  # noqa: BLE001 — never block the scheduler tick
                logger.exception("file_size_patrol work source failed")
                results["sources"][source_id] = {"error": "file_size_patrol_failed"}
            continue
        if source_id == "ci_remediation":
            # Webhook remains primary; scheduler only recovers leases above.
            results["sources"][source_id] = {
                "work_source": "ci_remediation",
                "mode": "recover_only",
            }
    return results


__all__ = [
    "load_work_source_config",
    "list_enabled_work_sources",
    "recover_orphaned_remediation_leases",
    "run_scheduled_work_sources",
]
