"""Host context bridge, artifacts, reminders, and privacy controls."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.host_context import reminders as reminder_engine
from app.host_context import service as host_service
from app.persistence.operator_memory_store import create_memory

router = APIRouter(tags=["host-context"])


class HostSnapshotIngestRequest(BaseModel):
    device_id: str = ""
    snapshot: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)


class HostArtifactsUpsertRequest(BaseModel):
    device_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class HostActionRequest(BaseModel):
    device_id: str
    action: str
    command_id: str = ""
    path: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class HostReceiptRequest(BaseModel):
    device_id: str
    receipt: dict[str, Any]


class HostPauseRequest(BaseModel):
    paused: bool = True


class ReminderCreateRequest(BaseModel):
    workspace_id: str = ""
    scope: str = "personal"
    title: str
    content: str
    due_at: str
    trigger: str = "time"
    priority: str = "normal"
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class ReminderPatchRequest(BaseModel):
    due_at: str | None = None
    snoozed_until: str | None = None
    trigger: str | None = None
    priority: str | None = None
    status: str | None = None
    last_presented_at: str | None = None
    dismiss_reason: str | None = None
    title: str | None = None
    content: str | None = None


@router.get("/api/host/capabilities")
def host_capabilities() -> dict[str, Any]:
    return host_service.get_capabilities()


@router.get("/api/host/policy")
def host_policy_get() -> dict[str, Any]:
    return host_service.get_policy()


@router.post("/api/host/privacy/pause")
def host_privacy_pause(body: HostPauseRequest) -> dict[str, Any]:
    return host_service.pause_awareness(body.paused)


@router.post("/api/host/bridge/snapshot")
def host_bridge_snapshot(body: HostSnapshotIngestRequest) -> dict[str, Any]:
    snapshot = body.snapshot if isinstance(body.snapshot, dict) else {}
    return host_service.ingest_snapshot(
        snapshot,
        device_id=body.device_id.strip() or None,
        events=body.events,
    )


@router.post("/api/host/artifacts")
def host_artifacts_upsert(body: HostArtifactsUpsertRequest) -> dict[str, Any]:
    device_id = body.device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    return host_service.upsert_artifacts(body.items, device_id=device_id)


@router.get("/api/host/artifacts")
def host_artifacts_list(
    device_id: str = "",
    query: str = "",
    limit: int = Query(default=40, ge=1, le=200),
) -> dict[str, Any]:
    return host_service.list_artifacts(
        device_id=device_id.strip() or None,
        query=query,
        limit=limit,
    )


@router.get("/api/host/events")
def host_events_list(
    device_id: str = "",
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return host_service.list_events(device_id=device_id.strip() or None, limit=limit)


@router.get("/api/host/receipts")
def host_receipts_list(
    device_id: str = "",
    limit: int = Query(default=40, ge=1, le=200),
) -> dict[str, Any]:
    return host_service.list_receipts(device_id=device_id.strip() or None, limit=limit)


@router.post("/api/host/actions/request")
def host_action_request(body: HostActionRequest) -> dict[str, Any]:
    device_id = body.device_id.strip()
    action = body.action.strip()
    if not device_id or not action:
        raise HTTPException(status_code=400, detail="device_id and action are required")
    return host_service.request_action(
        action=action,
        device_id=device_id,
        command_id=body.command_id,
        path=body.path,
        meta=body.meta,
    )


@router.post("/api/host/actions/receipt")
def host_action_receipt(body: HostReceiptRequest) -> dict[str, Any]:
    device_id = body.device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    return host_service.record_receipt(body.receipt, device_id=device_id)


@router.get("/api/host/reminders")
def host_reminders_list(
    workspace_id: str = "",
    due_only: bool = Query(default=True),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict[str, Any]:
    scoped = workspace_id.strip() or None
    if due_only:
        items = reminder_engine.due_reminders(workspace_id=scoped, limit=limit)
    else:
        items = reminder_engine.list_open_loops(workspace_id=scoped, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/api/host/reminders")
def host_reminders_create(body: ReminderCreateRequest) -> dict[str, Any]:
    title = body.title.strip()
    content = body.content.strip()
    due_at = body.due_at.strip()
    if not title or not content or not due_at:
        raise HTTPException(status_code=400, detail="title, content, and due_at are required")
    from app.host_context.models import utc_now_iso

    return create_memory(
        workspace_id=body.workspace_id.strip(),
        scope=body.scope.strip() or "personal",
        kind="reminder",
        title=title,
        content=content,
        source_refs=body.source_refs,
        created_at=utc_now_iso(),
        due_at=due_at,
        trigger=body.trigger.strip() or "time",
        priority=body.priority.strip() or "normal",
        status="open",
    )


@router.patch("/api/host/reminders/{memory_id}")
def host_reminders_patch(memory_id: str, body: ReminderPatchRequest) -> dict[str, Any]:
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="no reminder fields to patch")
    record = reminder_engine.patch_reminder(memory_id, patch)
    if record is None:
        raise HTTPException(status_code=404, detail="reminder not found")
    return record


@router.post("/api/host/reminders/migrate-whatsapp-g42")
def host_reminders_migrate_whatsapp() -> dict[str, Any]:
    record = reminder_engine.migrate_whatsapp_g42_reminder()
    return {"ok": True, "reminder": record}
