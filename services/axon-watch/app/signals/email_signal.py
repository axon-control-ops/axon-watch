"""Inbox projections for email triage signals."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from app.signals.email_imap_poll import fetch_native_email_messages
from app.signals.email_reply_suggest import suggest_email_reply
from app.signals.email_triage import analyze_email_message
from app.signals.iso_time import utc_now_iso

_PRIORITY_THRESHOLD = 50
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")

_DEFAULT_WORKSPACE_HINT_MAP: dict[str, str] = {
    "dashpro": "workspace_dashpro",
    "dash pro": "workspace_dashpro",
    "axon": "workspace_axon_watch",
    "axon watch": "workspace_axon_watch",
    "axon-watch": "workspace_axon_watch",
}


def _normalize_hint_key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def resolve_email_workspace_id(
    *,
    fallback_workspace_id: str,
    workspace_hints: list[str] | None = None,
    workspace_hint_map: dict[str, str] | None = None,
) -> str:
    """Map triage workspace hints to Axon-X string workspace IDs."""

    merged: dict[str, str] = dict(_DEFAULT_WORKSPACE_HINT_MAP)
    for raw_key, raw_value in (workspace_hint_map or {}).items():
        key = _normalize_hint_key(str(raw_key or ""))
        value = str(raw_value or "").strip()
        if key and value:
            merged[key] = value

    for hint in workspace_hints or []:
        key = _normalize_hint_key(str(hint or ""))
        if not key:
            continue
        mapped = merged.get(key) or merged.get(key.replace(" ", ""))
        if mapped:
            return mapped
    return str(fallback_workspace_id or "workspace_axon_watch").strip() or "workspace_axon_watch"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_email_stub_file() -> Path:
    configured = os.environ.get("AXON_WATCH_EMAIL_STUB_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "email-monitor-stub.json").resolve()


def _email_bridge_enabled() -> bool:
    projection = _load_operator_email_settings()
    if "bridge_enabled" in projection:
        return bool(projection.get("bridge_enabled"))
    raw = os.environ.get("AXON_WATCH_EMAIL_BRIDGE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _load_operator_email_settings() -> dict[str, Any]:
    configured = os.environ.get("AXON_WATCH_EMAIL_SETTINGS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
    else:
        path = (_repo_root() / "config" / "email-operator-settings.json").resolve()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_signal_token(value: str) -> str:
    cleaned = _SAFE_ID_RE.sub("_", value.strip())[:80].strip("_")
    return cleaned or "unknown"


def _severity_for_risk(risk_level: str) -> str:
    normalized = risk_level.strip().lower()
    if normalized == "high":
        return "high"
    if normalized == "medium":
        return "warning"
    return "info"


def _load_stub_config(path: Path | None = None) -> dict[str, Any]:
    stub_path = path or default_email_stub_file()
    if not stub_path.is_file():
        return {"enabled": False, "messages": [], "workspace_id": "workspace_axon_watch"}
    try:
        payload = json.loads(stub_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "messages": [], "workspace_id": "workspace_axon_watch"}
    if not isinstance(payload, dict):
        return {"enabled": False, "messages": [], "workspace_id": "workspace_axon_watch"}
    return payload


def _messages_from_stub(config: dict[str, Any]) -> list[dict[str, Any]]:
    if not bool(config.get("enabled", True)):
        return []
    messages = config.get("messages")
    if not isinstance(messages, list):
        return []
    return [dict(item) for item in messages if isinstance(item, dict)]


def _messages_from_live_bridge() -> list[dict[str, Any]] | None:
    _email_bridge_enabled()
    return None


def load_email_messages(
    *,
    stub_path: Path | None = None,
    force: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load email messages: native IMAP → Signal bridge → optional stub."""

    stub_config = _load_stub_config(stub_path)
    operator_settings = _load_operator_email_settings()
    if isinstance(operator_settings.get("workspace_hint_map"), dict):
        stub_config = dict(stub_config)
        merged_hints = dict(stub_config.get("workspace_hint_map") or {})
        merged_hints.update(
            {
                str(k): str(v)
                for k, v in operator_settings["workspace_hint_map"].items()
                if str(k).strip() and str(v).strip()
            }
        )
        stub_config["workspace_hint_map"] = merged_hints
    if operator_settings.get("accounts"):
        # Keep a generic fallback for stubs/bridge, but native messages carry
        # per-account workspace ownership and must not inherit accounts[0].
        stub_config = dict(stub_config)
        account_workspaces: dict[str, str] = {}
        for entry in operator_settings["accounts"]:
            if not isinstance(entry, dict):
                continue
            account_id = str(entry.get("account_id") or "").strip()
            account_email = str(entry.get("email_address") or "").strip().lower()
            workspace_id = str(entry.get("workspace_id") or "").strip()
            if workspace_id and account_id:
                account_workspaces[account_id] = workspace_id
            if workspace_id and account_email:
                account_workspaces[account_email] = workspace_id
        stub_config["account_workspaces"] = account_workspaces

    native = fetch_native_email_messages(force=force)
    if native is not None:
        return native, stub_config

    live = _messages_from_live_bridge()
    if live is not None:
        return live, stub_config

    if operator_settings.get("stub_enabled") is False:
        return [], stub_config
    return _messages_from_stub(stub_config), stub_config


def email_inbox_item(
    analysis: dict[str, Any],
    *,
    workspace_id: str,
) -> dict[str, object] | None:
    priority = int(analysis.get("priority") or 0)
    if priority < _PRIORITY_THRESHOLD:
        return None

    subject = str(analysis.get("subject") or "(no subject)").strip()
    sender = str(analysis.get("sender") or "Unknown sender").strip()
    message_id = str(analysis.get("message_id") or subject).strip()
    risk_level = str(analysis.get("risk_level") or "low").strip().lower()
    recommended_action = str(analysis.get("recommended_action") or "monitor_email").strip()
    recommended_detail = str(analysis.get("recommended_detail") or "").strip()
    snippet = str(analysis.get("snippet") or "").strip()
    account_id = str(analysis.get("account_id") or "").strip()
    account_email = str(analysis.get("account_email") or "").strip()
    account_token = account_id or account_email
    signal_token = (
        f"{_safe_signal_token(account_token)}_{_safe_signal_token(message_id)}"
        if account_token
        else _safe_signal_token(message_id)
    )
    now = utc_now_iso()
    # A no-reply sender cannot receive a reply at all (it bounces or is
    # discarded server-side), so no draft is generated -- previously this ran
    # unconditionally, drafted a full reply, and stored it regardless of what
    # analyze_email_message had already concluded about the sender.
    no_reply_sender = bool(analysis.get("no_reply_sender"))
    # Pass the already-computed analysis (full-text based) straight through --
    # not a message dict rebuilt from the truncated 280-char snippet, which
    # used to make suggest_email_reply re-run analyze_email_message on a
    # shorter, sometimes mid-sentence-truncated copy of the same email and
    # reach a different (worse) recommended_action than the one above.
    suggestion = {} if no_reply_sender else suggest_email_reply(analysis)

    return {
        "signal_id": f"signal_email_{signal_token}",
        "workspace_id": workspace_id,
        "title": f"Email needs follow-up: {subject}",
        "summary": f"{sender} — {recommended_detail}".strip(" —"),
        "severity": _severity_for_risk(risk_level),
        "status": "open",
        "source": "email",
        "created_at": now,
        "updated_at": now,
        "action_type": "investigate",
        "delivery_state": "pending",
        "meta": {
            "signal_family": "email_triage",
            "message_id": message_id,
            "sender": sender,
            "subject": subject,
            "snippet": snippet,
            "recommended_action": str(suggestion.get("recommended_action") or recommended_action),
            "recommended_detail": str(suggestion.get("recommended_detail") or recommended_detail),
            "priority": priority,
            "risk_level": risk_level,
            "action_requests": list(analysis.get("action_requests") or [])[:5],
            "risks": list(analysis.get("risks") or [])[:5],
            "commitments": list(analysis.get("commitments") or [])[:5],
            "due_markers": list(analysis.get("due_markers") or [])[:5],
            "workspace_hints": list(analysis.get("workspace_hints") or [])[:5],
            "suggested_reply_subject": suggestion.get("reply_subject") if not no_reply_sender else None,
            "suggested_reply_body": suggestion.get("reply_body") if not no_reply_sender else None,
            "no_reply_sender": no_reply_sender,
            "email_account_id": account_id,
            "email_account_address": account_email,
        },
    }


def _mapped_hint_workspace(
    workspace_hints: list[str],
    workspace_hint_map: dict[str, str],
) -> str:
    """Return a hint-mapped workspace id, or empty when no hint matches."""

    merged: dict[str, str] = dict(_DEFAULT_WORKSPACE_HINT_MAP)
    for raw_key, raw_value in workspace_hint_map.items():
        key = _normalize_hint_key(str(raw_key or ""))
        value = str(raw_value or "").strip()
        if key and value:
            merged[key] = value
    for hint in workspace_hints:
        key = _normalize_hint_key(str(hint or ""))
        if not key:
            continue
        mapped = merged.get(key) or merged.get(key.replace(" ", ""))
        if mapped:
            return mapped
    return ""


def _workspace_for_message(
    message: dict[str, Any],
    *,
    account_workspaces: dict[str, str],
    fallback_workspace_id: str,
    workspace_hints: list[str],
    workspace_hint_map: dict[str, str],
) -> str:
    """Prefer the mailbox's configured workspace over generic body hints."""

    account_id = str(message.get("account_id") or "").strip()
    account_email = str(message.get("account_email") or "").strip().lower()
    mailbox_workspace = (
        account_workspaces.get(account_id)
        or account_workspaces.get(account_email)
        or ""
    )
    if mailbox_workspace:
        return mailbox_workspace
    hinted = _mapped_hint_workspace(workspace_hints, workspace_hint_map)
    if hinted:
        return hinted
    return (
        str(fallback_workspace_id or "").strip()
        or "workspace_axon_watch"
    )


def email_inbox_items(
    *,
    stub_path: Path | None = None,
    force: bool = False,
) -> list[dict[str, object]]:
    messages, config = load_email_messages(stub_path=stub_path, force=force)
    fallback_workspace_id = str(config.get("workspace_id") or "workspace_axon_watch").strip()
    workspace_names = [
        str(name).strip()
        for name in (config.get("workspace_names") or [])
        if str(name).strip()
    ]
    raw_hint_map = config.get("workspace_hint_map")
    workspace_hint_map = (
        {str(k): str(v) for k, v in raw_hint_map.items() if str(k).strip() and str(v).strip()}
        if isinstance(raw_hint_map, dict)
        else {}
    )
    raw_account_map = config.get("account_workspaces")
    account_workspaces = (
        {str(k): str(v) for k, v in raw_account_map.items() if str(k).strip() and str(v).strip()}
        if isinstance(raw_account_map, dict)
        else {}
    )

    items: list[dict[str, object]] = []
    for message in messages:
        analysis = analyze_email_message(message, workspace_names=workspace_names)
        workspace_id = _workspace_for_message(
            message,
            account_workspaces=account_workspaces,
            fallback_workspace_id=fallback_workspace_id,
            workspace_hints=list(analysis.get("workspace_hints") or []),
            workspace_hint_map=workspace_hint_map,
        )
        item = email_inbox_item(analysis, workspace_id=workspace_id)
        if item is not None:
            items.append(item)
    return items
