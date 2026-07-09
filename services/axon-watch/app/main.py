"""Minimal FastAPI shell for the watch service bootstrap slice."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.commands.executor import WatchCommandError
from app.commands.service import get_watch_command, submit_watch_command
from app.connectors.summary import probe_all_connectors
from app.data.snapshot import operator_data_snapshot
from app.delivery.store import delivery_summary, list_receipts
from app.events.store import list_events
from app.events.stream import watch_events_stream_response
from app.signals.inbox_assembly import include_summary_degraded_signal
from app.signals.store import get_inbox_snapshot
from app.tunnel.tunnel_control import TunnelControlError, tunnel_start, tunnel_status, tunnel_stop
from app.vault.api import (
    VaultExportBody,
    VaultMonitorImportBody,
    VaultSecretBody,
    VaultSetupBody,
    VaultUnlockBody,
    handle_auto_unlock_disable,
    handle_auto_unlock_enable,
    handle_auto_unlock_status,
    handle_create_secret,
    handle_delete_secret,
    handle_export_backup,
    handle_export_csv,
    handle_get_secret,
    handle_import_backup,
    handle_list_secrets,
    handle_monitor_import,
    handle_provider_keys,
    handle_runtime_env,
    handle_runtime_posture,
    handle_update_secret,
    handle_vault_lock,
    handle_vault_setup,
    handle_vault_status,
    handle_vault_unlock,
)
from app.vault.operations import attempt_auto_unlock
from app.watch_summary import build_connectors_response, build_watch_summary
from app.monitors.monitor_snapshot import build_monitors_response


def _state_dir() -> str:
    return os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state")


def _dashpro_project_root() -> Path | None:
    config_path = Path(__file__).resolve().parents[3] / "config" / "dashpro-monitor-slice.json"
    if not config_path.is_file():
        return None
    import json

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    root_raw = str(payload.get("project_root") or "").strip()
    return Path(root_raw).expanduser() if root_raw else None


class WatchCommandBody(BaseModel):
    command_id: str | None = None
    command_type: str
    target_type: str = ""
    target_id: str = ""
    requested_by: str = "control-plane"
    payload: dict[str, object] | None = None
    requested_at: str | None = None


app = FastAPI(
    title="Axon-X Watch Service",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


@app.on_event("startup")
def vault_startup_auto_unlock() -> None:
    attempt_auto_unlock()


@app.get("/internal/watch/health")
def health() -> dict[str, str]:
    return {
        "service": "axon-watch",
        "status": "ok",
        "mode": "bootstrap",
    }


@app.get("/internal/watch/readiness")
def readiness() -> dict[str, object]:
    connectors = build_connectors_response()
    summary = connectors.get("summary", {})
    connector_items = connectors.get("items")
    records = connector_items if isinstance(connector_items, list) else None
    degraded_expected = include_summary_degraded_signal(connector_records=records)
    return {
        "service": "axon-watch",
        "status": "ready",
        "mode": "bootstrap",
        "state_dir": _state_dir(),
        "dependencies": {
            "connectors_configured": summary.get("configured", 0),
            "connectors_ok": summary.get("ok", 0),
            "connectors_required_unavailable": summary.get("required_unavailable", 0),
        },
        "bootstrap_notes": {
            "summary_degraded_signal_expected": degraded_expected,
            "detail": (
                "Bootstrap may emit a stale runtime-summary signal until required "
                "connector probes are trusted; connector probes and watch "
                "commands/events are available on dedicated routes."
            ),
        },
    }


@app.get("/internal/watch/summary")
def summary() -> dict[str, object]:
    return build_watch_summary()


@app.get("/internal/watch/connectors")
def connectors() -> dict[str, object]:
    return build_connectors_response()


@app.get("/internal/watch/tunnel")
def tunnel_index() -> dict[str, object]:
    return tunnel_status()


@app.post("/internal/watch/tunnel/start")
def tunnel_start_route() -> dict[str, object]:
    try:
        return tunnel_start()
    except TunnelControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/internal/watch/tunnel/stop")
def tunnel_stop_route() -> dict[str, object]:
    try:
        return tunnel_stop()
    except TunnelControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/internal/watch/monitors")
def monitors() -> dict[str, object]:
    return build_monitors_response()


@app.get("/internal/watch/inbox")
def inbox() -> dict[str, object]:
    return get_inbox_snapshot(connector_records=probe_all_connectors())


@app.get("/internal/watch/vault/status")
def vault_status_index() -> dict[str, object]:
    return handle_vault_status(project_root=_dashpro_project_root())


@app.get("/internal/watch/vault/provider-keys")
def vault_provider_keys_index() -> dict[str, object]:
    return handle_provider_keys()


@app.get("/internal/watch/vault/runtime-posture")
def vault_runtime_posture_index() -> dict[str, object]:
    return handle_runtime_posture()


@app.get("/internal/watch/vault/runtime-env")
def vault_runtime_env_index() -> dict[str, object]:
    return handle_runtime_env()


@app.post("/internal/watch/vault/setup")
def vault_setup_index(body: VaultSetupBody) -> dict[str, object]:
    return handle_vault_setup(body)


@app.post("/internal/watch/vault/unlock")
def vault_unlock_index(body: VaultUnlockBody) -> dict[str, object]:
    return handle_vault_unlock(body)


@app.post("/internal/watch/vault/lock")
def vault_lock_index() -> dict[str, object]:
    return handle_vault_lock()


@app.get("/internal/watch/vault/auto-unlock/status")
def vault_auto_unlock_status_index() -> dict[str, object]:
    return handle_auto_unlock_status()


@app.post("/internal/watch/vault/auto-unlock/enable")
def vault_auto_unlock_enable_index() -> dict[str, object]:
    return handle_auto_unlock_enable()


@app.post("/internal/watch/vault/auto-unlock/disable")
def vault_auto_unlock_disable_index() -> dict[str, object]:
    return handle_auto_unlock_disable()


@app.get("/internal/watch/vault/secrets")
def vault_secrets_list_index() -> list[dict[str, object]]:
    return handle_list_secrets()


@app.get("/internal/watch/vault/secrets/{secret_id}")
def vault_secrets_show_index(secret_id: int) -> dict[str, object]:
    return handle_get_secret(secret_id)


@app.post("/internal/watch/vault/secrets")
def vault_secrets_create_index(body: VaultSecretBody) -> dict[str, object]:
    return handle_create_secret(body)


@app.put("/internal/watch/vault/secrets/{secret_id}")
def vault_secrets_update_index(secret_id: int, body: VaultSecretBody) -> dict[str, object]:
    return handle_update_secret(secret_id, body)


@app.delete("/internal/watch/vault/secrets/{secret_id}")
def vault_secrets_delete_index(secret_id: int) -> dict[str, object]:
    return handle_delete_secret(secret_id)


@app.post("/internal/watch/vault/export")
def vault_export_backup_index(body: VaultExportBody):
    return handle_export_backup(body)


@app.get("/internal/watch/vault/export/csv")
def vault_export_csv_index(format: str = Query(default="axon")):
    return handle_export_csv(format)


@app.post("/internal/watch/vault/import")
async def vault_import_backup_index(
    backup_password: str = Form(""),
    mode: str = Form("merge"),
    file: UploadFile = File(...),
) -> dict[str, object]:
    return await handle_import_backup(backup_password=backup_password, mode=mode, file=file)


@app.post("/internal/watch/vault/import/monitor-keys")
def vault_import_monitor_keys_index(body: VaultMonitorImportBody) -> dict[str, object]:
    return handle_monitor_import(body)


@app.get("/internal/watch/data/snapshot")
def data_snapshot_index(limit: int = Query(default=50, ge=1, le=100)) -> dict[str, object]:
    return {"data": operator_data_snapshot(limit=limit)}


@app.get("/internal/watch/delivery/receipts")
def delivery_receipts_index(
    limit: int = Query(20, ge=1, le=100),
    cursor: str = Query(""),
) -> dict[str, object]:
    return list_receipts(limit=limit, cursor=cursor)


@app.post("/internal/watch/commands")
def commands_create(body: WatchCommandBody) -> dict[str, object]:
    try:
        return submit_watch_command(body.model_dump())
    except WatchCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/internal/watch/commands/{command_id}")
def commands_show(command_id: str) -> dict[str, object]:
    try:
        return get_watch_command(command_id)
    except WatchCommandError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/internal/watch/events")
def events_index(
    limit: int = Query(20, ge=1, le=100),
    cursor: str = Query(""),
) -> dict[str, object]:
    return list_events(limit=limit, cursor=cursor)


@app.get("/internal/watch/events/stream")
def events_stream():
    return watch_events_stream_response()
