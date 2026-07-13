"""Evidence projection for operator brain nodes."""

from __future__ import annotations

from typing import Any

from app.adapters.watch_client import fetch_watch_connectors
from app.inbox_projection import build_inbox_response
from app.runs.service import get_run, get_run_history, list_active_runs
from app.workspace_catalog import get_workspace_record, list_workspace_records


def _source_ref(
    ref_type: str,
    ref_id: str,
    *,
    label: str,
    workspace_id: str = "",
) -> dict[str, str]:
    return {
        "ref_type": ref_type,
        "ref_id": ref_id,
        "label": label,
        "workspace_id": workspace_id,
    }


def _workspace_evidence(workspace_id: str) -> dict[str, Any]:
    record = get_workspace_record(workspace_id)
    signals = [
        item
        for item in build_inbox_response().get("items", [])
        if isinstance(item, dict) and str(item.get("workspace_id", "")).strip() == workspace_id
    ][:5]
    runs = [
        run
        for run in list_active_runs()
        if str(run.get("workspace_id", "")).strip() == workspace_id
    ][:5]
    return {
        "node_id": f"ws_{workspace_id}",
        "kind": "workspace",
        "title": str(record.get("display_name") or workspace_id),
        "summary": f"{len(runs)} active run(s) · {len(signals)} open signal(s)",
        "facts": [
            {"label": "Workspace", "value": workspace_id},
            {"label": "Binding", "value": str(record.get("connection_kind") or "unknown")},
            {"label": "Signals", "value": str(len(signals))},
            {"label": "Active runs", "value": str(len(runs))},
        ],
        "sources": [_source_ref("workspace", workspace_id, label="Workspace catalog", workspace_id=workspace_id)],
        "actions": [
            {"label": "Open workspace in IDE", "target": "workspace", "workspace_id": workspace_id},
        ],
        "sections": [
            {
                "title": "Signals",
                "items": [
                    {
                        "title": str(signal.get("title") or signal.get("signal_id") or "Signal"),
                        "detail": str(signal.get("summary") or signal.get("severity") or "").strip(),
                        "source_ref": _source_ref(
                            "signal",
                            str(signal.get("signal_id") or ""),
                            label="Inbox signal",
                            workspace_id=workspace_id,
                        ),
                    }
                    for signal in signals
                ],
            },
            {
                "title": "Runs",
                "items": [
                    {
                        "title": str(run.get("summary") or run.get("run_id") or "Run"),
                        "detail": str(run.get("phase") or "").strip(),
                        "source_ref": _source_ref(
                            "run",
                            str(run.get("run_id") or ""),
                            label="Run state",
                            workspace_id=workspace_id,
                        ),
                    }
                    for run in runs
                ],
            },
        ],
    }


def _run_evidence(run_id: str) -> dict[str, Any]:
    record = get_run(run_id)
    history = get_run_history(run_id).get("items", [])[:8]
    workspace_id = str(record.get("workspace_id") or "")
    return {
        "node_id": f"run_{run_id}",
        "kind": "run",
        "title": str(record.get("summary") or run_id),
        "summary": str(record.get("phase") or "unknown"),
        "facts": [
            {"label": "Run", "value": run_id},
            {"label": "Phase", "value": str(record.get("phase") or "")},
            {"label": "Current step", "value": str(record.get("current_step") or "none")},
        ],
        "sources": [_source_ref("run", run_id, label="Run history", workspace_id=workspace_id)],
        "actions": [
            {"label": "Open workspace in IDE", "target": "workspace", "workspace_id": workspace_id},
        ],
        "sections": [
            {
                "title": "Receipts",
                "items": [
                    {
                        "title": str(item.get("receipt", {}).get("type") or item.get("to_phase") or "transition"),
                        "detail": str(item.get("receipt", {}).get("summary") or item.get("current_step") or ""),
                        "source_ref": _source_ref("run", run_id, label="Run history", workspace_id=workspace_id),
                    }
                    for item in history
                ],
            }
        ],
    }


def _signal_evidence(signal_id: str) -> dict[str, Any]:
    signal = next(
        (
            item
            for item in build_inbox_response().get("items", [])
            if isinstance(item, dict) and str(item.get("signal_id", "")).strip() == signal_id
        ),
        None,
    )
    if signal is None:
        raise ValueError(f"signal not found: {signal_id}")
    workspace_id = str(signal.get("workspace_id") or "")
    return {
        "node_id": f"sig_{signal_id}",
        "kind": "signal",
        "title": str(signal.get("title") or signal_id),
        "summary": str(signal.get("summary") or signal.get("severity") or ""),
        "facts": [
            {"label": "Signal", "value": signal_id},
            {"label": "Severity", "value": str(signal.get("severity") or "info")},
            {"label": "Status", "value": str(signal.get("status") or "open")},
        ],
        "sources": [_source_ref("signal", signal_id, label="Inbox signal", workspace_id=workspace_id)],
        "actions": [
            {"label": "Open in Attention", "target": "signal", "signal_id": signal_id},
            {"label": "Open workspace in IDE", "target": "workspace", "workspace_id": workspace_id},
        ],
        "sections": [],
    }


def _connector_evidence(connector_id: str) -> dict[str, Any]:
    connectors = fetch_watch_connectors() or {}
    item = next(
        (
            row
            for row in connectors.get("items", [])
            if isinstance(row, dict) and str(row.get("connector_id", "")).strip() == connector_id
        ),
        None,
    )
    if item is None:
        raise ValueError(f"connector not found: {connector_id}")
    workspace_id = str(item.get("workspace_id") or "")
    return {
        "node_id": f"conn_{connector_id}",
        "kind": "connector",
        "title": str(item.get("display_name") or connector_id),
        "summary": str(item.get("status") or "unknown"),
        "facts": [
            {"label": "Connector", "value": connector_id},
            {"label": "Status", "value": str(item.get("status") or "unknown")},
            {"label": "Workspace", "value": workspace_id or "fleet"},
        ],
        "sources": [_source_ref("connector", connector_id, label="Connector probe", workspace_id=workspace_id)],
        "actions": [
            {"label": "Open workspace in IDE", "target": "workspace", "workspace_id": workspace_id},
        ],
        "sections": [],
    }


def _core_evidence() -> dict[str, Any]:
    workspaces = list_workspace_records(operator_surface=True)
    active_runs = list_active_runs()
    return {
        "node_id": "core_kairo",
        "kind": "core",
        "title": "VAXON control plane",
        "summary": "Control plane, watch, runs, and connectors",
        "facts": [
            {"label": "Visible workspaces", "value": str(len(workspaces))},
            {"label": "Active runs", "value": str(len(active_runs))},
        ],
        "sources": [_source_ref("core", "core_kairo", label="Control-plane projection")],
        "actions": [],
        "sections": [],
    }


def build_operator_evidence(node_id: str) -> dict[str, Any]:
    clean = str(node_id or "").strip()
    if clean == "core_kairo":
        return _core_evidence()
    if clean.startswith("ws_"):
        return _workspace_evidence(clean.removeprefix("ws_"))
    if clean.startswith("run_"):
        return _run_evidence(clean.removeprefix("run_"))
    if clean.startswith("sig_"):
        return _signal_evidence(clean.removeprefix("sig_"))
    if clean.startswith("conn_"):
        return _connector_evidence(clean.removeprefix("conn_"))
    raise ValueError(f"unsupported node id: {clean}")

