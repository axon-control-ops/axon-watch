"""CLI runtime readiness summary for operator truth surfaces."""

from __future__ import annotations

from typing import Any


def _local_records(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    records = snapshot.get("local")
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _blocker_message(record: dict[str, Any]) -> str:
    runtime_id = str(record.get("id") or "runtime")
    label = str(record.get("label") or runtime_id)
    # Unavailable binary beats a misleading "Authenticated…" auth overlay.
    if not record.get("available"):
        return f"{label} unavailable"
    auth = record.get("auth") if isinstance(record.get("auth"), dict) else {}
    message = str(auth.get("message") or "").strip()
    if message:
        return f"{label}: {message}"
    return f"{label} not dispatch-ready"


def summarize_cli_runtime_readiness(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Summarize whether any local CLI runtime can dispatch Lane B work."""
    local = _local_records(snapshot)
    ready_records = [record for record in local if record.get("ready")]
    default_runtime = str(snapshot.get("default_runtime") or "")
    default_record = next(
        (record for record in local if str(record.get("id") or "") == default_runtime),
        None,
    )
    blockers = [_blocker_message(record) for record in local if not record.get("ready")]
    return {
        "dispatch_ready": bool(ready_records),
        "ready_count": len(ready_records),
        "local_count": len(local),
        "default_runtime": default_runtime,
        "default_ready": bool(default_record.get("ready")) if default_record else False,
        "blockers": blockers,
        # Empty local list is stale-while-revalidate bootstrap, not a proven outage.
        "probe_pending": len(local) == 0,
    }


def cli_runtime_degraded_reasons(snapshot: dict[str, Any]) -> list[str]:
    """Return degraded reasons when no local CLI runtime is dispatch-ready."""
    local = _local_records(snapshot)
    if not local:
        # Empty snapshot from allow_stale bootstrap must not flash false CLI degraded.
        return []
    summary = summarize_cli_runtime_readiness(snapshot)
    if summary["dispatch_ready"]:
        return []
    blockers = [str(item).strip() for item in summary.get("blockers", []) if str(item).strip()]
    if blockers:
        return [f"CLI runtime not ready — {blockers[0]}"]
    return ["CLI runtime not ready — no local CLI runtime is dispatch-ready"]
