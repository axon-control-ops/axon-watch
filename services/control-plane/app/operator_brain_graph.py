"""Brain graph projection for operator second-brain visualization (OP-B6a).

Nodes and edges are derived from live run, signal, connector, and workspace
truth. Layout (2D/3D positions) is client-side; this DTO never stores
coordinates. The graph is a visualization contract, not an alternate source
of truth.
"""

from __future__ import annotations

from typing import Any, Callable

from app.adapters.watch_client import fetch_watch_connectors
from app.domain.run_state import is_terminal_phase
from app.inbox_projection import WatchInboxFetcher, build_inbox_response
from app.persistence import email_settings_store
from app.runs.service import list_runs
from app.runtime_summary_assembler import WatchProbe, assemble_runtime_summary
from app.operator_persona_name import OPERATOR_PERSONA_NAME
from app.workspace_catalog import list_workspace_records

ConnectorsFetcher = Callable[[], dict[str, object] | None]

_CORE_NODE_ID = "core_kairo"
_MAX_RUN_NODES_PER_WORKSPACE = 3
_MAX_SIGNAL_NODES = 6


def _workspace_tone(
    *,
    pending_approvals: int,
    critical_signals: int,
    review_ready: int,
    executing: int,
    open_signals: int,
) -> str:
    if pending_approvals > 0 or critical_signals > 0:
        return "critical"
    if review_ready > 0 or executing > 0 or open_signals > 0:
        return "attention"
    return "nominal"


def _connector_tone(status: str) -> str:
    if status == "ok":
        return "nominal"
    if status == "degraded":
        return "attention"
    return "critical"


def _signal_tone(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "critical"
    return "attention"


def _mailbox_tone(account: dict[str, Any]) -> str:
    imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
    smtp = account.get("smtp") if isinstance(account.get("smtp"), dict) else {}
    has_password = bool(str(imap.get("password_ref") or "").strip()) or bool(
        str(smtp.get("password_ref") or "").strip()
    )
    monitor = account.get("monitor") if isinstance(account.get("monitor"), dict) else {}
    if not has_password:
        return "attention"
    if not bool(monitor.get("enabled", True)):
        return "attention"
    return "nominal"


def _append_mailbox_nodes(
    *,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    workspace_node_ids: set[str],
) -> None:
    try:
        settings = email_settings_store.load_settings()
    except Exception:  # noqa: BLE001 — graph must stay available if settings store fails
        return
    accounts = settings.get("accounts") if isinstance(settings, dict) else []
    if not isinstance(accounts, list):
        return
    for account in accounts:
        if not isinstance(account, dict):
            continue
        account_id = str(account.get("account_id") or "").strip()
        email_address = str(account.get("email_address") or "").strip()
        workspace_id = str(account.get("workspace_id") or "").strip()
        if not account_id or not email_address:
            continue
        imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
        has_password = bool(str(imap.get("password_ref") or "").strip())
        node_id = f"mail_{account_id}"
        nodes.append(
            {
                "node_id": node_id,
                "kind": "mailbox",
                "label": email_address,
                "tone": _mailbox_tone(account),
                "workspace_id": workspace_id or None,
                "detail": (
                    f"{imap.get('host') or 'no-host'} · "
                    f"{'ready' if has_password else 'needs password'}"
                ),
            }
        )
        source = (
            f"ws_{workspace_id}"
            if workspace_id and f"ws_{workspace_id}" in workspace_node_ids
            else _CORE_NODE_ID
        )
        edges.append(
            {
                "edge_id": f"monitors_mail_{account_id}",
                "source": source,
                "target": node_id,
                "kind": "monitors",
            }
        )


def build_operator_brain_graph(
    *,
    watch_probe: WatchProbe | None = None,
    inbox_fetcher: WatchInboxFetcher | None = None,
    connectors_fetcher: ConnectorsFetcher | None = None,
) -> dict[str, object]:
    runtime_summary = assemble_runtime_summary(
        watch_probe=watch_probe,
        inbox_fetcher=inbox_fetcher,
    )
    watch_connected = bool(runtime_summary["watch"]["connected"])
    generated_at = str(runtime_summary["generated_at"])

    inbox_snapshot = (
        build_inbox_response(inbox_fetcher=inbox_fetcher)
        if watch_connected
        else {"items": [], "count": 0, "updated_at": generated_at}
    )
    signals = [
        item
        for item in inbox_snapshot.get("items", [])
        if isinstance(item, dict) and item.get("status") == "open"
    ][:_MAX_SIGNAL_NODES]

    connectors_loader = connectors_fetcher or fetch_watch_connectors
    connectors_payload = connectors_loader() if watch_connected else None
    connector_items = [
        item
        for item in (connectors_payload or {}).get("items", [])
        if isinstance(item, dict)
    ]

    active_runs = [
        record
        for record in list_runs()
        if not is_terminal_phase(str(record.get("phase", "")))
    ]

    workspace_records = list_workspace_records(
        inbox_fetcher=inbox_fetcher,
        operator_surface=True,
    )
    runs_by_workspace: dict[str, list[dict[str, Any]]] = {}
    for run in active_runs:
        runs_by_workspace.setdefault(str(run.get("workspace_id", "")), []).append(run)

    signal_workspace_ids = {
        str(signal.get("workspace_id", "")).strip()
        for signal in signals
        if str(signal.get("workspace_id", "")).strip()
    }
    connector_workspace_ids = {
        str(item.get("workspace_id", "")).strip()
        for item in connector_items
        if str(item.get("workspace_id", "")).strip()
    }

    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []

    core_tone = "nominal"
    if bool(runtime_summary["degraded"]["active"]):
        core_tone = "attention"
    nodes.append(
        {
            "node_id": _CORE_NODE_ID,
            "kind": "core",
            "label": OPERATOR_PERSONA_NAME,
            "tone": core_tone,
            "workspace_id": None,
            "detail": "Control plane + watch brain",
        }
    )

    # Meaningful workspaces only: bound projects, active runs, signals, or connectors.
    for workspace in workspace_records:
        workspace_id = str(workspace["workspace_id"])
        is_bound = workspace.get("connection_kind") == "project_path"
        workspace_runs = runs_by_workspace.get(workspace_id, [])
        has_signal = workspace_id in signal_workspace_ids
        has_connector = workspace_id in connector_workspace_ids
        if not (is_bound or workspace_runs or has_signal or has_connector):
            continue

        review_ready = sum(1 for run in workspace_runs if run.get("phase") == "review_ready")
        executing = sum(1 for run in workspace_runs if run.get("phase") == "executing")
        pending_approvals = sum(
            1 for run in workspace_runs if run.get("phase") == "awaiting_approval"
        )
        workspace_signals = [
            signal
            for signal in signals
            if str(signal.get("workspace_id", "")).strip() == workspace_id
        ]
        critical_signals = sum(
            1
            for signal in workspace_signals
            if signal.get("severity") in {"critical", "high"}
        )

        node_id = f"ws_{workspace_id}"
        nodes.append(
            {
                "node_id": node_id,
                "kind": "workspace",
                "label": str(workspace.get("display_name") or workspace_id),
                "tone": _workspace_tone(
                    pending_approvals=pending_approvals,
                    critical_signals=critical_signals,
                    review_ready=review_ready,
                    executing=executing,
                    open_signals=len(workspace_signals),
                ),
                "workspace_id": workspace_id,
                "detail": f"{len(workspace_runs)} active run(s) · {len(workspace_signals)} signal(s)",
            }
        )
        edges.append(
            {
                "edge_id": f"member_{workspace_id}",
                "source": _CORE_NODE_ID,
                "target": node_id,
                "kind": "member",
            }
        )

        for run in workspace_runs[-_MAX_RUN_NODES_PER_WORKSPACE:]:
            run_id = str(run.get("run_id", ""))
            run_node_id = f"run_{run_id}"
            phase = str(run.get("phase", ""))
            nodes.append(
                {
                    "node_id": run_node_id,
                    "kind": "run",
                    "label": str(run.get("summary") or run_id),
                    "tone": "critical" if phase == "awaiting_approval" else "attention",
                    "workspace_id": workspace_id,
                    "detail": phase,
                }
            )
            edges.append(
                {
                    "edge_id": f"executes_{run_id}",
                    "source": node_id,
                    "target": run_node_id,
                    "kind": "executes",
                }
            )
        overflow = len(workspace_runs) - _MAX_RUN_NODES_PER_WORKSPACE
        if overflow > 0:
            overflow_node_id = f"runs_more_{workspace_id}"
            nodes.append(
                {
                    "node_id": overflow_node_id,
                    "kind": "run",
                    "label": f"+{overflow} more runs",
                    "tone": "attention",
                    "workspace_id": workspace_id,
                    "detail": "collapsed",
                }
            )
            edges.append(
                {
                    "edge_id": f"executes_more_{workspace_id}",
                    "source": node_id,
                    "target": overflow_node_id,
                    "kind": "executes",
                }
            )

    workspace_node_ids = {
        str(node["node_id"])
        for node in nodes
        if node["kind"] == "workspace"
    }

    for signal in signals:
        signal_id = str(signal.get("signal_id", ""))
        workspace_id = str(signal.get("workspace_id", "")).strip()
        node_id = f"sig_{signal_id}"
        nodes.append(
            {
                "node_id": node_id,
                "kind": "signal",
                "label": str(signal.get("title") or signal_id),
                "tone": _signal_tone(str(signal.get("severity", "info"))),
                "workspace_id": workspace_id or None,
                "detail": str(signal.get("severity", "info")),
            }
        )
        source = (
            f"ws_{workspace_id}"
            if workspace_id and f"ws_{workspace_id}" in workspace_node_ids
            else _CORE_NODE_ID
        )
        edges.append(
            {
                "edge_id": f"emits_{signal_id}",
                "source": source,
                "target": node_id,
                "kind": "emits",
            }
        )

    for item in connector_items:
        connector_id = str(item.get("connector_id", ""))
        workspace_id = str(item.get("workspace_id", "")).strip()
        node_id = f"conn_{connector_id}"
        nodes.append(
            {
                "node_id": node_id,
                "kind": "connector",
                "label": str(item.get("display_name") or connector_id),
                "tone": _connector_tone(str(item.get("status", "unavailable"))),
                "workspace_id": workspace_id or None,
                "detail": str(item.get("status", "unavailable")),
            }
        )
        source = (
            f"ws_{workspace_id}"
            if workspace_id and f"ws_{workspace_id}" in workspace_node_ids
            else _CORE_NODE_ID
        )
        edges.append(
            {
                "edge_id": f"monitors_{connector_id}",
                "source": source,
                "target": node_id,
                "kind": "monitors",
            }
        )

    _append_mailbox_nodes(
        nodes=nodes,
        edges=edges,
        workspace_node_ids=workspace_node_ids,
    )

    return {
        "generated_at": generated_at,
        "watch_connected": watch_connected,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
