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
            # Webhook is the fast path. Reconcile durable task outcomes when a
            # GitHub completion arrived while the local control plane was down.
            from app.ci_remediation.report import reconcile_linked_repair_task_outcomes

            results["sources"][source_id] = {
                "work_source": "ci_remediation",
                "reconciled": reconcile_linked_repair_task_outcomes(),
            }
            continue
        if source_id == "lead_team_checkin" and "scheduler" in trigger:
            from app.workspace_agents.lead_team_checkin import run_lead_team_checkin
            from app.persistence import operator_presence_settings_store

            min_interval = float(source.get("min_interval_seconds") or 900)
            max_assign = int(source.get("max_assignments_per_workspace") or 2)
            # Full autonomy attend owns specialist task creation — avoid dual
            # Lead assigned: + VAXON attend: rows for the same failed_shift.
            settings = operator_presence_settings_store.load_settings()
            mode = str(settings.get("autonomy_mode") or "manual").strip().lower()
            if mode == "full":
                max_assign = 0
            try:
                results["sources"][source_id] = run_lead_team_checkin(
                    min_interval_seconds=min_interval,
                    max_assignments_per_workspace=max_assign,
                )
            except Exception:  # noqa: BLE001 — never block the scheduler tick
                logger.exception("lead_team_checkin work source failed")
                results["sources"][source_id] = {"error": "lead_team_checkin_failed"}
            continue
        if source_id == "ci_stale_signal_sweep" and "scheduler" in trigger:
            from app.ci_remediation.stale_sweep import sweep_stale_ci_signals

            try:
                results["sources"][source_id] = sweep_stale_ci_signals(
                    include_drills=bool(source.get("include_drills", True)),
                    confirm_with_gh=bool(source.get("confirm_with_gh", True)),
                    max_resolve=int(source.get("max_resolve") or 40),
                )
            except Exception:  # noqa: BLE001
                logger.exception("ci_stale_signal_sweep work source failed")
                results["sources"][source_id] = {"error": "ci_stale_signal_sweep_failed"}
            continue
        if source_id == "fleet_self_heal_detect" and "scheduler" in trigger:
            # VAXON fleet self-heal detect stage — always-on infrastructure
            # health, like ci_remediation/ci_stale_signal_sweep above, not
            # gated by per-workspace autonomy_mode.
            from app.fleet_self_heal.config import load_fleet_self_heal_config
            from app.fleet_self_heal.detect import scan_fleet_failures
            from app.fleet_self_heal.dispatch import dispatch_dispatchable_fingerprints
            from app.fleet_self_heal.report import reconcile_linked_fleet_repair_outcomes

            try:
                reconciled = reconcile_linked_fleet_repair_outcomes()
                result = scan_fleet_failures(
                    window_hours=(
                        float(source["window_hours"]) if "window_hours" in source else None
                    ),
                    min_interval_seconds=(
                        float(source["min_interval_seconds"])
                        if "min_interval_seconds" in source
                        else None
                    ),
                )
                dispatched: list[dict[str, Any]] = []
                if result.dispatchable_fingerprints or result.regressed_fingerprints:
                    dispatched = dispatch_dispatchable_fingerprints(
                        config=load_fleet_self_heal_config(),
                        fingerprints=[
                            *result.dispatchable_fingerprints,
                            *result.regressed_fingerprints,
                        ],
                    )
                results["sources"][source_id] = {
                    "work_source": "fleet_self_heal_detect",
                    "reconciled": reconciled,
                    "scanned_runs": result.scanned_runs,
                    "fleet_infra_observations": result.fleet_infra_observations,
                    "dispatchable_fingerprints": result.dispatchable_fingerprints,
                    "regressed_fingerprints": result.regressed_fingerprints,
                    "dispatched_count": len(dispatched),
                    "skipped_min_interval": result.skipped_min_interval,
                }
            except Exception:  # noqa: BLE001 — never block the scheduler tick
                logger.exception("fleet_self_heal_detect work source failed")
                results["sources"][source_id] = {"error": "fleet_self_heal_detect_failed"}
            continue
        if source_id == "autonomous_attention" and "scheduler" in trigger:
            from app.workspace_agents.autonomous_attention import run_autonomous_attention_scan
            from app.persistence import operator_presence_settings_store

            settings = operator_presence_settings_store.load_settings()
            mode = str(settings.get("autonomy_mode") or "manual").strip().lower()
            if mode != "full":
                results["sources"][source_id] = {
                    "work_source": "autonomous_attention",
                    "skipped": True,
                    "reason": f"autonomy_mode={mode}",
                }
                continue
            try:
                results["sources"][source_id] = run_autonomous_attention_scan(
                    max_dispatch_per_workspace=int(
                        source.get("max_dispatch_per_workspace") or 3
                    ),
                    max_escalations_per_workspace=int(
                        source.get("max_escalations_per_workspace") or 5
                    ),
                    # lead_team_checkin remains its own source; avoid double message spam
                    include_lead_checkin=False,
                )
            except Exception:  # noqa: BLE001 — never block the scheduler tick
                logger.exception("autonomous_attention work source failed")
                results["sources"][source_id] = {"error": "autonomous_attention_failed"}
            continue
    return results


__all__ = [
    "load_work_source_config",
    "list_enabled_work_sources",
    "recover_orphaned_remediation_leases",
    "run_scheduled_work_sources",
]
