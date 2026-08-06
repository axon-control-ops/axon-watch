"""Scan fleet run history for repeat/breadth failure clusters and regressions.

Detect is the entry point wired into the scheduler (company_work_sources.py).
It processes each newly-failed run exactly once (tracked via a persisted
high-water mark, same JSON-state-file pattern as
scheduler_auto_start_gates.py's cooldown files) so a fingerprint's
occurrence_count reflects distinct failures, not re-scans of the same run on
every tick.

``window_hours`` is enforced as a recency gate on dispatch — an event only
becomes dispatchable while its most recent occurrence is still within the
window, so a long-dormant fingerprint that quietly reoccurs once doesn't ride
in on a stale occurrence_count built up months apart.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.fleet_self_heal import store
from app.fleet_self_heal.classify import classify_failure_signature
from app.fleet_self_heal.config import FleetSelfHealConfig, load_fleet_self_heal_config
from app.persistence import run_store

logger = logging.getLogger(__name__)

_RAW_FAILURE_RECEIPT_TYPES = {
    "run_failed",
    "runtime_dispatch",
    "finalization_error",
    "control_plane_restart",
}


@dataclass(frozen=True)
class DetectScanResult:
    scanned_runs: int
    fleet_infra_observations: int
    dispatchable_fingerprints: list[str]
    regressed_fingerprints: list[str]
    skipped_min_interval: bool


def _state_path() -> Path:
    raw = os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state").strip() or "./.local/state"
    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root / "fleet-self-heal-scan-state.json"


def _load_state(path: Path | None = None) -> dict[str, Any]:
    target = path or _state_path()
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_state(state: dict[str, Any], path: Path | None = None) -> None:
    target = path or _state_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        logger.exception("could not persist fleet self-heal scan state")


def _parse_iso(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _raw_failure_text_for_run(run: dict[str, Any]) -> str:
    """Untruncated failure text — run_outcome.py's latest_role_run_outcome()
    truncates to 180 chars, too short for a traceback; this mirrors its
    receipt-type priority order without that truncation."""
    history_ref = str(run.get("history_ref") or "").strip()
    if not history_ref:
        return str(run.get("current_step") or "")
    for item in reversed(run_store.list_history(history_ref)):
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "").strip() in _RAW_FAILURE_RECEIPT_TYPES:
            summary = str(receipt.get("summary") or "").strip()
            if summary:
                return summary
    return str(run.get("current_step") or "")


def scan_fleet_failures(
    *,
    window_hours: float | None = None,
    min_interval_seconds: float | None = None,
    config: FleetSelfHealConfig | None = None,
    now: datetime | None = None,
    state_path: Path | None = None,
) -> DetectScanResult:
    cfg = config or load_fleet_self_heal_config()
    if not cfg.enabled:
        return DetectScanResult(0, 0, [], [], skipped_min_interval=False)

    window = window_hours if window_hours is not None else cfg.window_hours
    interval = min_interval_seconds if min_interval_seconds is not None else cfg.min_scan_interval_seconds
    current = now or datetime.now(timezone.utc)

    state = _load_state(state_path)
    last_scan_at = _parse_iso(state.get("last_scan_at"))
    if last_scan_at is not None and (current - last_scan_at).total_seconds() < interval:
        return DetectScanResult(0, 0, [], [], skipped_min_interval=True)

    high_water_mark = _parse_iso(state.get("high_water_mark"))
    scan_since = high_water_mark or (current - timedelta(hours=window))
    since_iso = scan_since.isoformat().replace("+00:00", "Z")

    failed_runs = run_store.list_failed_runs_since(since_iso)
    fleet_infra_count = 0
    newest_updated_at = high_water_mark
    touched_fingerprints: set[str] = set()

    for run in failed_runs:
        updated_at = _parse_iso(str(run.get("updated_at") or ""))
        if updated_at is not None and (newest_updated_at is None or updated_at > newest_updated_at):
            newest_updated_at = updated_at
        if high_water_mark is not None and updated_at is not None and updated_at <= high_water_mark:
            continue  # already processed on a prior tick

        detail = _raw_failure_text_for_run(run)
        signature = classify_failure_signature(detail=detail)
        if signature.category != "fleet_infra":
            continue

        prior = store.get_event(signature.fingerprint)
        was_verified_fixed = bool(prior and prior.get("status") == "verified_fixed")
        resolution_verified_at = _parse_iso(prior.get("resolution_verified_at")) if prior else None

        event = store.upsert_observation(
            signature.fingerprint,
            subsystem=signature.subsystem,
            file_hint=signature.file_hint,
            workspace_id=str(run.get("workspace_id") or ""),
            role=str(run.get("employee_role") or ""),
            run_id=str(run.get("run_id") or ""),
            observed_at=str(run.get("updated_at") or ""),
        )
        fleet_infra_count += 1
        touched_fingerprints.add(signature.fingerprint)

        if was_verified_fixed and resolution_verified_at is not None:
            failure_time = updated_at or current
            if failure_time > resolution_verified_at:
                store.set_event_status(signature.fingerprint, "regressed")

    dispatchable: list[str] = []
    regressed: list[str] = []
    for fingerprint in touched_fingerprints:
        event = store.get_event(fingerprint)
        if event is None:
            continue
        if event["status"] == "regressed":
            regressed.append(fingerprint)
            continue
        if event["status"] not in {"observed", "blocked"}:
            continue  # already dispatched/repairing/verified_fixed — nothing new to do
        last_seen = _parse_iso(event.get("last_seen_at"))
        if last_seen is None or (current - last_seen).total_seconds() > window * 3600:
            continue  # stale cluster, outside the recency window
        workspaces = event.get("workspaces_json") or []
        roles = event.get("roles_json") or []
        pairs = {(w, r) for w, r in zip(workspaces, roles)}
        repeat_hit = len(pairs) == 1 and event["occurrence_count"] >= cfg.repeat_occurrence_threshold
        breadth_hit = len(pairs) >= cfg.breadth_pair_threshold
        if repeat_hit or breadth_hit:
            dispatchable.append(fingerprint)

    state["last_scan_at"] = current.isoformat().replace("+00:00", "Z")
    if newest_updated_at is not None:
        state["high_water_mark"] = newest_updated_at.isoformat().replace("+00:00", "Z")
    _save_state(state, state_path)

    return DetectScanResult(
        scanned_runs=len(failed_runs),
        fleet_infra_observations=fleet_infra_count,
        dispatchable_fingerprints=dispatchable,
        regressed_fingerprints=regressed,
        skipped_min_interval=False,
    )


__all__ = ["DetectScanResult", "scan_fleet_failures"]
