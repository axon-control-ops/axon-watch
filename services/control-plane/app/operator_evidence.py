"""Evidence projection for operator brain nodes."""

from __future__ import annotations

from typing import Any

from app.adapters.watch_client import fetch_watch_connectors
from app.inbox_projection import build_inbox_response
from app.persistence import email_settings_store
from app.runs.service import get_run, get_run_history, list_operator_facing_active_runs
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
        for run in list_operator_facing_active_runs()
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
    meta = signal.get("meta") if isinstance(signal.get("meta"), dict) else {}
    facts = [
        {"label": "Signal", "value": signal_id},
        {"label": "Severity", "value": str(signal.get("severity") or "info")},
        {"label": "Status", "value": str(signal.get("status") or "open")},
        {"label": "Source", "value": str(signal.get("source") or "unknown")},
        {"label": "Action", "value": str(signal.get("action_type") or "none")},
        {"label": "Delivery", "value": str(signal.get("delivery_state") or "pending")},
    ]
    if str(meta.get("check_id") or "").strip():
        facts.append({"label": "Monitor check", "value": str(meta.get("check_id"))})
    if str(meta.get("monitor_status") or "").strip():
        facts.append({"label": "Monitor status", "value": str(meta.get("monitor_status"))})
    if str(meta.get("signal_family") or "").strip():
        facts.append({"label": "Family", "value": str(meta.get("signal_family"))})
    if str(meta.get("sender") or "").strip():
        facts.append({"label": "Sender", "value": str(meta.get("sender"))})
    if str(meta.get("subject") or "").strip():
        facts.append({"label": "Subject", "value": str(meta.get("subject"))})
    if str(meta.get("recommended_action") or "").strip():
        facts.append({"label": "Recommended action", "value": str(meta.get("recommended_action"))})

    sections: list[dict[str, Any]] = []
    if str(meta.get("signal_family") or "").strip() == "email_triage":
        detail_items: list[dict[str, Any]] = []
        snippet = str(meta.get("snippet") or "").strip()
        if snippet:
            detail_items.append(
                {
                    "title": "Snippet",
                    "detail": snippet,
                    "source_ref": _source_ref(
                        "signal",
                        signal_id,
                        label="Email triage",
                        workspace_id=workspace_id,
                    ),
                }
            )
        recommended_detail = str(meta.get("recommended_detail") or "").strip()
        if recommended_detail:
            detail_items.append(
                {
                    "title": "Recommended detail",
                    "detail": recommended_detail,
                    "source_ref": _source_ref(
                        "signal",
                        signal_id,
                        label="Email triage",
                        workspace_id=workspace_id,
                    ),
                }
            )
        if detail_items:
            sections.append({"title": "Email", "items": detail_items})

        risks = meta.get("risks")
        if isinstance(risks, list) and risks:
            sections.append(
                {
                    "title": "Risks",
                    "items": [
                        {
                            "title": str(risk),
                            "detail": "",
                            "source_ref": _source_ref(
                                "signal",
                                signal_id,
                                label="Email triage",
                                workspace_id=workspace_id,
                            ),
                        }
                        for risk in risks
                        if str(risk).strip()
                    ][:5],
                }
            )

        action_requests = meta.get("action_requests")
        if isinstance(action_requests, list) and action_requests:
            sections.append(
                {
                    "title": "Action requests",
                    "items": [
                        {
                            "title": str(action),
                            "detail": "",
                            "source_ref": _source_ref(
                                "signal",
                                signal_id,
                                label="Email triage",
                                workspace_id=workspace_id,
                            ),
                        }
                        for action in action_requests
                        if str(action).strip()
                    ][:5],
                }
            )

    sentry_issues = meta.get("sentry_issues")
    if isinstance(sentry_issues, list) and sentry_issues:
        sections.append(
            {
                "title": "Sentry issues",
                "items": [
                    {
                        "title": str(issue.get("title") or issue.get("id") or "Issue"),
                        "detail": (
                            f"count={issue.get('count', '?')}"
                            + (
                                f" · {issue.get('permalink')}"
                                if str(issue.get("permalink") or "").strip()
                                else ""
                            )
                        ),
                        "source_ref": _source_ref(
                            "sentry_issue",
                            str(issue.get("id") or issue.get("shortId") or ""),
                            label=str(issue.get("permalink") or "Sentry issue"),
                            workspace_id=workspace_id,
                        ),
                    }
                    for issue in sentry_issues
                    if isinstance(issue, dict)
                ][:8],
            }
        )

    return {
        "node_id": f"sig_{signal_id}",
        "kind": "signal",
        "title": str(signal.get("title") or signal_id),
        "summary": str(signal.get("summary") or signal.get("severity") or ""),
        "facts": facts,
        "sources": [_source_ref("signal", signal_id, label="Inbox signal", workspace_id=workspace_id)],
        "actions": [
            {"label": "Open in Attention", "target": "signal", "signal_id": signal_id},
            {
                "label": "Continue in IDE",
                "target": "handoff",
                "signal_id": signal_id,
                "workspace_id": workspace_id,
            },
            {"label": "Open workspace in IDE", "target": "workspace", "workspace_id": workspace_id},
        ],
        "sections": sections,
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
    active_runs = list_operator_facing_active_runs()
    primary_workspace_id = ""
    preferred_ids = (
        "workspace_axon_watch",
        "workspace_axon_local",
        "workspace_axon",
    )
    by_id = {
        str(record.get("workspace_id") or "").strip(): record
        for record in workspaces
        if str(record.get("workspace_id") or "").strip()
    }
    for preferred in preferred_ids:
        if preferred in by_id:
            primary_workspace_id = preferred
            break
    if not primary_workspace_id and by_id:
        primary_workspace_id = next(iter(by_id))
    actions: list[dict[str, Any]] = []
    if primary_workspace_id:
        actions.append(
            {
                "label": "Open in Workspace",
                "target": "workspace",
                "workspace_id": primary_workspace_id,
            }
        )
    return {
        "node_id": "core_kairo",
        "kind": "core",
        "title": "VAXON control plane",
        "summary": (
            "Primary knowledge hub and orchestration node for the operator brain — "
            "control plane, watch, runs, and connectors."
        ),
        "facts": [
            {"label": "Visible workspaces", "value": str(len(workspaces))},
            {"label": "Active runs", "value": str(len(active_runs))},
            {"label": "Role", "value": "Fleet orchestration core"},
            {"label": "Status", "value": "online"},
        ],
        "sources": [
            _source_ref(
                "core",
                "core_kairo",
                label="Control-plane projection",
                workspace_id=primary_workspace_id,
            )
        ],
        "actions": actions,
        "sections": [
            {
                "title": "System",
                "items": [
                    {
                        "title": "System initialization record",
                        "detail": "Control-plane projection online for the operator brain.",
                        "source_ref": _source_ref("core", "core_kairo", label="System Log"),
                    },
                    {
                        "title": "Watch fabric link",
                        "detail": "Signals and monitors feed attention into this core node.",
                        "source_ref": _source_ref("core", "core_kairo", label="Watch"),
                    },
                    {
                        "title": "Run orchestration index",
                        "detail": f"{len(active_runs)} active run(s) across the visible fleet.",
                        "source_ref": _source_ref("core", "core_kairo", label="Runs"),
                    },
                    {
                        "title": "Workspace catalog",
                        "detail": f"{len(workspaces)} operator-visible workspace(s) bound to the graph.",
                        "source_ref": _source_ref("core", "core_kairo", label="Catalog"),
                    },
                    {
                        "title": "Evidence projection",
                        "detail": "Node inspector loads prove-source facts for selected entities.",
                        "source_ref": _source_ref("core", "core_kairo", label="Evidence"),
                    },
                    {
                        "title": "Voice / command surface",
                        "detail": "VAXON conversation bar and orb remain live on the mission canvas.",
                        "source_ref": _source_ref("core", "core_kairo", label="VAXON"),
                    },
                ],
            }
        ],
    }


def _mailbox_evidence(account_id: str) -> dict[str, Any]:
    settings = email_settings_store.load_settings()
    account = None
    for entry in settings.get("accounts") or []:
        if isinstance(entry, dict) and str(entry.get("account_id") or "") == account_id:
            account = entry
            break
    if account is None:
        raise ValueError(f"mailbox not found: {account_id}")
    workspace_id = str(account.get("workspace_id") or "").strip()
    email_address = str(account.get("email_address") or "").strip()
    imap = account.get("imap") if isinstance(account.get("imap"), dict) else {}
    smtp = account.get("smtp") if isinstance(account.get("smtp"), dict) else {}
    monitor = account.get("monitor") if isinstance(account.get("monitor"), dict) else {}
    has_password = bool(str(imap.get("password_ref") or "").strip()) or bool(
        str(smtp.get("password_ref") or "").strip()
    )
    return {
        "node_id": f"mail_{account_id}",
        "kind": "mailbox",
        "title": email_address or account_id,
        "summary": (
            f"Mailbox for {workspace_id or 'unscoped workspace'} — "
            f"{'credentials ready' if has_password else 'needs password in Vault'}"
        ),
        "facts": [
            {"label": "Email", "value": email_address},
            {"label": "Workspace", "value": workspace_id or "—"},
            {"label": "IMAP host", "value": str(imap.get("host") or "—")},
            {"label": "IMAP folder", "value": str(imap.get("folder") or "INBOX")},
            {"label": "SMTP host", "value": str(smtp.get("host") or "—")},
            {
                "label": "Passwords",
                "value": "saved in Vault" if has_password else "missing — edit in Settings → Email",
            },
            {
                "label": "Monitor",
                "value": (
                    f"enabled · {monitor.get('poll_seconds', 60)}s"
                    if monitor.get("enabled", True)
                    else "disabled"
                ),
            },
        ],
        "sources": [
            _source_ref(
                "mailbox",
                account_id,
                label="Email settings",
                workspace_id=workspace_id,
            )
        ],
        "actions": [
            {
                "label": "Open workspace in IDE",
                "target": "workspace",
                "workspace_id": workspace_id,
            },
        ],
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
    if clean.startswith("mail_"):
        return _mailbox_evidence(clean.removeprefix("mail_"))
    raise ValueError(f"unsupported node id: {clean}")

