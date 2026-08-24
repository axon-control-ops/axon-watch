"""Inbox, monitors, connectors, tunnel, and watch integration routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.adapters.watch_client import (
    fetch_watch_connectors,
    fetch_watch_delivery_receipts,
    fetch_watch_email_folders,
    fetch_watch_email_messages,
    fetch_watch_events,
    fetch_watch_monitors,
    fetch_watch_tunnel,
    get_watch_command,
    post_watch_command,
    post_watch_sentry_issue_attend,
    post_watch_sentry_issue_resolve,
    post_watch_sentry_probe_write,
    post_watch_tunnel_action,
)
from app.email_account_resolve import resolve_workspace_email_account
from app.inbox_projection import WatchInboxUnavailableError, build_inbox_response
from app.inbox_signals import acknowledge_inbox_signals
from app.persistence import email_settings_store
from app.routes.schemas import (
    AcknowledgeInboxSignalsRequest,
    SentryAttendRequest,
    SentryResolveRequest,
    WatchCommandRequest,
)

router = APIRouter()


@router.get("/api/inbox")
def inbox(force: bool = False) -> dict[str, object]:
    try:
        return build_inbox_response(force_refresh=force)
    except WatchInboxUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _resolve_account_id(*, workspace_id: str = "", account_id: str = "") -> str:
    account_id = account_id.strip()
    if account_id:
        settings = email_settings_store.load_settings()
        for entry in settings.get("accounts") or []:
            if isinstance(entry, dict) and str(entry.get("account_id") or "") == account_id:
                return account_id
        raise HTTPException(
            status_code=404,
            detail=f"no mailbox configured for account_id: {account_id}",
        )

    workspace_id = workspace_id.strip()
    settings = email_settings_store.load_settings()
    account = resolve_workspace_email_account(settings, workspace_id=workspace_id)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"no mailbox configured for workspace: {workspace_id}",
        )
    return str(account.get("account_id") or "")


@router.get("/api/email/folders")
def email_folders(workspace_id: str = "", account_id: str = "") -> dict[str, object]:
    resolved_account_id = _resolve_account_id(workspace_id=workspace_id, account_id=account_id)
    payload = fetch_watch_email_folders(resolved_account_id)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch service unavailable")
    return payload


@router.get("/api/email/messages")
def email_messages(
    workspace_id: str = "",
    account_id: str = "",
    role: str = "inbox",
    limit: int = 25,
) -> dict[str, object]:
    resolved_account_id = _resolve_account_id(workspace_id=workspace_id, account_id=account_id)
    payload = fetch_watch_email_messages(resolved_account_id, role, limit=limit)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch service unavailable")
    return payload


@router.post("/api/inbox/signals/acknowledge")
def inbox_signals_acknowledge(body: AcknowledgeInboxSignalsRequest) -> dict[str, object]:
    result = acknowledge_inbox_signals(body.signal_ids)
    if not result.get("accepted"):
        raise HTTPException(
            status_code=503,
            detail=str(result.get("error", "signal acknowledgement unavailable")),
        )
    return result


@router.get("/api/monitors")
def monitors_index() -> dict[str, object]:
    payload = fetch_watch_monitors()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch monitors unavailable")
    return payload


@router.post("/api/sentry/issues/{issue_id}/resolve")
def sentry_issue_resolve(issue_id: str, body: SentryResolveRequest | None = None) -> dict[str, object]:
    request = body or SentryResolveRequest()
    payload = post_watch_sentry_issue_resolve(
        issue_id,
        status=request.status,
        requested_by=request.requested_by,
    )
    if payload is None:
        raise HTTPException(status_code=503, detail="watch sentry resolve unavailable")
    if not payload.get("ok"):
        raise HTTPException(status_code=400, detail=payload)
    return payload


@router.post("/api/sentry/issues/{issue_id}/attend")
def sentry_issue_attend(issue_id: str, body: SentryAttendRequest | None = None) -> dict[str, object]:
    request = body or SentryAttendRequest()
    payload = post_watch_sentry_issue_attend(
        issue_id,
        confirm_release=request.confirm_release,
        requested_by=request.requested_by,
        mark_resolved_in_next_release=request.mark_resolved_in_next_release,
        workspace_id=request.workspace_id,
    )
    if payload is None:
        raise HTTPException(status_code=503, detail="watch sentry attend unavailable")
    if not payload.get("ok"):
        raise HTTPException(status_code=400, detail=payload)
    return payload


@router.post("/api/sentry/probe-write")
def sentry_probe_write() -> dict[str, object]:
    payload = post_watch_sentry_probe_write()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch sentry write probe unavailable")
    return payload


@router.get("/api/connectors")
def connectors_index() -> dict[str, object]:
    payload = fetch_watch_connectors()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch connectors unavailable")
    return payload


@router.get("/api/tunnel/status")
def tunnel_status_index() -> dict[str, object]:
    payload = fetch_watch_tunnel()
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel status unavailable")
    return payload


@router.post("/api/tunnel/start")
def tunnel_start_index() -> dict[str, object]:
    payload = post_watch_tunnel_action("start")
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel start unavailable")
    return payload


@router.post("/api/tunnel/stop")
def tunnel_stop_index() -> dict[str, object]:
    payload = post_watch_tunnel_action("stop")
    if payload is None:
        raise HTTPException(status_code=503, detail="watch tunnel stop unavailable")
    return payload


@router.post("/api/watch/commands")
def watch_commands_create(body: WatchCommandRequest) -> dict[str, object]:
    payload = post_watch_command(body.model_dump())
    if payload is None:
        raise HTTPException(status_code=503, detail="watch command submission unavailable")
    return payload


@router.get("/api/watch/commands/{command_id}")
def watch_commands_show(command_id: str) -> dict[str, object]:
    payload = get_watch_command(command_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"watch command not found: {command_id}")
    return payload


@router.get("/api/watch/events")
def watch_events_index(limit: int = 20, cursor: str = "") -> dict[str, object]:
    payload = fetch_watch_events(limit=limit, cursor=cursor)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch events unavailable")
    return payload


@router.get("/api/delivery/receipts")
def delivery_receipts_index(limit: int = 20, cursor: str = "") -> dict[str, object]:
    payload = fetch_watch_delivery_receipts(limit=limit, cursor=cursor)
    if payload is None:
        raise HTTPException(status_code=503, detail="watch delivery receipts unavailable")
    return payload
