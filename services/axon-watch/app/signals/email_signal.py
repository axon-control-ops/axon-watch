"""Inbox projections for email triage signals."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from app.connectors.catalog import load_watch_connector_definitions
from app.connectors.probe import probe_connector
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
    "axon local": "workspace_axon_local",
    "axon-local": "workspace_axon_local",
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


def _axon_local_base_url() -> str | None:
    definitions = load_watch_connector_definitions()
    definition = definitions.get("axon_local")
    if definition is None:
        return None
    record = probe_connector(definition)
    if str(record.get("status") or "") != "ok":
        return None
    parts = urlsplit(definition.health_url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def _messages_from_live_bridge() -> list[dict[str, Any]] | None:
    if not _email_bridge_enabled():
        return None
    base_url = _axon_local_base_url()
    if not base_url:
        return None

    workspace_id = os.environ.get("AXON_WATCH_EMAIL_BRIDGE_WORKSPACE_ID", "").strip()
    if not workspace_id:
        workspace_id = str(_load_operator_email_settings().get("bridge_workspace_id") or "7").strip() or "7"
    url = urljoin(
        base_url.rstrip("/") + "/",
        f"api/connectors/email/workspaces/{workspace_id}/analysis?limit=10&force=false",
    )
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=1.5) as response:
            body = response.read(256_000).decode("utf-8", errors="replace")
            payload = json.loads(body)
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    messages: list[dict[str, Any]] = []
    for entry in payload.get("analyses") or []:
        if not isinstance(entry, dict):
            continue
        message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
        analysis = entry.get("analysis") if isinstance(entry.get("analysis"), dict) else {}
        text = str(analysis.get("snippet") or "").strip()
        if not text:
            # Prefer recommended detail as fallback snippet when bridge omits body text.
            text = str(analysis.get("recommended_detail") or "").strip()
        messages.append(
            {
                "message_id": str(message.get("message_id") or analysis.get("message_id") or "").strip(),
                "uid": str(message.get("uid") or "").strip(),
                "from": str(message.get("from") or analysis.get("sender") or "").strip(),
                "subject": str(message.get("subject") or analysis.get("subject") or "").strip(),
                "text": text,
                "snippet": text,
            }
        )
    return messages


def load_email_messages(
    *,
    stub_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load email messages from live bridge when healthy, else stub config."""

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
    now = utc_now_iso()

    return {
        "signal_id": f"signal_email_{_safe_signal_token(message_id)}",
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
            "sender": sender,
            "subject": subject,
            "snippet": snippet,
            "recommended_action": recommended_action,
            "recommended_detail": recommended_detail,
            "priority": priority,
            "risk_level": risk_level,
            "action_requests": list(analysis.get("action_requests") or [])[:5],
            "risks": list(analysis.get("risks") or [])[:5],
            "commitments": list(analysis.get("commitments") or [])[:5],
            "due_markers": list(analysis.get("due_markers") or [])[:5],
            "workspace_hints": list(analysis.get("workspace_hints") or [])[:5],
        },
    }


def email_inbox_items(
    *,
    stub_path: Path | None = None,
) -> list[dict[str, object]]:
    messages, config = load_email_messages(stub_path=stub_path)
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

    items: list[dict[str, object]] = []
    for message in messages:
        analysis = analyze_email_message(message, workspace_names=workspace_names)
        workspace_id = resolve_email_workspace_id(
            fallback_workspace_id=fallback_workspace_id,
            workspace_hints=list(analysis.get("workspace_hints") or []),
            workspace_hint_map=workspace_hint_map,
        )
        item = email_inbox_item(analysis, workspace_id=workspace_id)
        if item is not None:
            items.append(item)
    return items
