"""Host-context service facade used by HTTP routes and brain graph."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.host_context import store
from app.host_context.models import (
    normalize_artifact,
    normalize_event,
    normalize_receipt,
    normalize_snapshot,
    utc_now_iso,
)
from app.host_context.policy import evaluate_action_request


def get_policy() -> dict[str, Any]:
    return store.load_policy()


def pause_awareness(paused: bool) -> dict[str, Any]:
    policy = store.load_policy()
    policy["awareness_paused"] = bool(paused)
    return store.save_policy(policy)


def get_capabilities() -> dict[str, Any]:
    policy = store.load_policy()
    devices = store.list_devices(limit=10)
    snapshot = store.latest_snapshot()
    return {
        "runtime": "desktop" if devices else "browser",
        "awareness_paused": bool(policy.get("awareness_paused")),
        "devices": devices,
        "latest_snapshot": snapshot,
        "action_tiers": {
            "auto": "metadata and reversible convenience",
            "confirm": "exact-effect approval required",
            "deny": "blocked until explicitly enabled",
        },
        "retention_days": int(policy.get("retention_days") or 14),
    }


def ingest_snapshot(
    raw: dict[str, Any],
    *,
    device_id: str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    policy = store.load_policy()
    if policy.get("awareness_paused"):
        return {
            "accepted": False,
            "reason": "host_awareness_paused",
            "snapshot": None,
            "events": [],
        }
    resolved_device = str(device_id or raw.get("device_id") or f"device_{uuid4().hex[:12]}")
    snapshot = normalize_snapshot(raw, device_id=resolved_device)
    store.upsert_snapshot(snapshot)
    store.prune_expired()
    accepted_events: list[dict[str, Any]] = []
    for item in events or []:
        if not isinstance(item, dict):
            continue
        event = normalize_event(item, device_id=resolved_device)
        store.insert_event(event)
        accepted_events.append(event)
    return {
        "accepted": True,
        "reason": "ok",
        "snapshot": snapshot,
        "events": accepted_events,
    }


def upsert_artifacts(
    items: list[dict[str, Any]],
    *,
    device_id: str,
) -> dict[str, Any]:
    policy = store.load_policy()
    if policy.get("awareness_paused"):
        return {"accepted": False, "count": 0, "items": [], "reason": "host_awareness_paused"}
    written: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record = normalize_artifact(item, device_id=device_id)
        if not record["path"] and not record["title"]:
            continue
        store.upsert_artifact(record)
        written.append(record)
    return {"accepted": True, "count": len(written), "items": written, "reason": "ok"}


def list_artifacts(*, device_id: str | None = None, query: str = "", limit: int = 40) -> dict[str, Any]:
    items = store.list_artifacts(device_id=device_id, query=query, limit=limit)
    return {"items": items, "count": len(items)}


def list_events(*, device_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    items = store.list_events(device_id=device_id, limit=limit)
    return {"items": items, "count": len(items)}


def list_receipts(*, device_id: str | None = None, limit: int = 40) -> dict[str, Any]:
    items = store.list_receipts(device_id=device_id, limit=limit)
    return {"items": items, "count": len(items)}


def request_action(
    *,
    action: str,
    device_id: str,
    command_id: str = "",
    path: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = store.load_policy()
    resolved_command = str(command_id or "").strip() or f"cmd_{uuid4().hex}"
    if store.command_seen(resolved_command):
        return {
            "accepted": False,
            "replay": True,
            "command_id": resolved_command,
            "decision": {
                "allowed": False,
                "tier": "deny",
                "reason": "replay_rejected",
                "requires_approval": False,
            },
            "receipt": None,
        }
    decision = evaluate_action_request(
        action=action,
        path=path,
        awareness_paused=bool(policy.get("awareness_paused")),
        deny_overrides_enabled=bool(policy.get("deny_overrides_enabled")),
    )
    receipt = None
    if decision["allowed"]:
        receipt = normalize_receipt(
            {
                "command_id": resolved_command,
                "action": action,
                "tier": decision["tier"],
                "status": "queued",
                "result_summary": "Accepted for desktop bridge execution",
                "meta": meta or {},
            },
            device_id=device_id,
        )
        store.insert_receipt(receipt)
    elif decision.get("requires_approval"):
        receipt = normalize_receipt(
            {
                "command_id": resolved_command,
                "action": action,
                "tier": decision["tier"],
                "status": "awaiting_approval",
                "result_summary": str(decision.get("reason") or "approval_required"),
                "meta": {"path": path or "", **(meta or {})},
            },
            device_id=device_id,
        )
        store.insert_receipt(receipt)
    else:
        receipt = normalize_receipt(
            {
                "command_id": resolved_command,
                "action": action,
                "tier": decision["tier"],
                "status": "denied",
                "result_summary": str(decision.get("reason") or "denied"),
                "meta": meta or {},
            },
            device_id=device_id,
        )
        store.insert_receipt(receipt)
    return {
        "accepted": bool(decision["allowed"]),
        "replay": False,
        "command_id": resolved_command,
        "decision": decision,
        "receipt": receipt,
        "evaluated_at": utc_now_iso(),
    }


def record_receipt(raw: dict[str, Any], *, device_id: str) -> dict[str, Any]:
    record = normalize_receipt(raw, device_id=device_id)
    if record.get("command_id") and store.command_seen(record["command_id"]):
        # Allow terminal status updates by inserting a follow-up receipt id.
        record["receipt_id"] = f"hrcpt_{uuid4().hex}"
    store.insert_receipt(record)
    return record
