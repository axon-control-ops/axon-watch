"""Session-scoped turn and entity memory for KAIRO follow-ups (OP-C5)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_MAX_TURN_MEMORY = 8

_TURN_MEMORY: dict[str, list[dict[str, str]]] = {}
_ENTITY_MEMORY: dict[str, dict[str, str]] = {}

_HANDOFF_ACTION_RE = re.compile(
    r"\b(hand\s*it\s*off|hand\s*off|handoff|continue in ide|investigate in ide|open in ide)\b",
    re.IGNORECASE,
)
_CONFIRM_RE = re.compile(r"^(yes|yeah|yep|do it|confirm|go ahead)\.?$", re.IGNORECASE)
_BRIEFING_SURFACE_OFFER_RE = re.compile(
    r"\b(pull\s+(?:it\s+)?to\s+the\s+front|bring\s+(?:it\s+)?(?:up|forward)|"
    r"open\s+the\s+briefing|shall\s+i\s+(?:pull|show|open))\b",
    re.IGNORECASE,
)


def session_key(session_id: str) -> str:
    cleaned = str(session_id or "default").strip() or "default"
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


def remember_turn(session_id: str, role: str, content: str) -> None:
    key = session_key(session_id)
    bucket = _TURN_MEMORY.setdefault(key, [])
    bucket.append({"role": role, "content": content.strip()})
    if len(bucket) > _MAX_TURN_MEMORY:
        del bucket[: len(bucket) - _MAX_TURN_MEMORY]


def recent_turns(session_id: str) -> list[dict[str, str]]:
    return list(_TURN_MEMORY.get(session_key(session_id), []))


def remember_entities(session_id: str, **fields: str) -> None:
    key = session_key(session_id)
    bucket = _ENTITY_MEMORY.setdefault(key, {})
    for name, value in fields.items():
        cleaned = str(value or "").strip()
        if cleaned:
            bucket[name] = cleaned


def entity_context(session_id: str) -> dict[str, str]:
    return dict(_ENTITY_MEMORY.get(session_key(session_id), {}))


def remember_top_signal(
    session_id: str,
    pack: dict[str, Any],
    *,
    fallback_workspace_id: str | None = None,
) -> None:
    briefing = pack["briefing"]
    top_signals = [
        item for item in briefing.get("top_signals", []) if isinstance(item, dict)
    ]
    if not top_signals:
        return
    signal = top_signals[0]
    signal_id = str(signal.get("signal_id", "")).strip()
    if not signal_id:
        return
    workspace_id = (
        str(signal.get("workspace_id", "")).strip()
        or str(fallback_workspace_id or "").strip()
    )
    title = str(signal.get("title", "")).strip()
    summary = str(signal.get("summary", "")).strip()
    task = f'Investigate signal "{title}"'
    if summary:
        task = f"{task}: {summary}"
    remember_entities(
        session_id,
        signal_id=signal_id,
        target_workspace_id=workspace_id,
        signal_title=title,
        task=task,
    )


def note_briefing_surface_offer(session_id: str, reply: str) -> None:
    if _BRIEFING_SURFACE_OFFER_RE.search(str(reply or "")):
        remember_entities(session_id, pending_briefing_surface="1")


def resolve_followup_action(content: str, session_id: str) -> dict[str, object] | None:
    trimmed = content.strip()
    entity = entity_context(session_id)
    if _CONFIRM_RE.match(trimmed):
        pending_command = entity.get("pending_command", "")
        if pending_command:
            return {"type": "dispatch_command", "content": pending_command}
        if entity.get("pending_briefing_surface") == "1":
            return {"type": "focus_briefing"}
    if _HANDOFF_ACTION_RE.search(trimmed):
        signal_id = entity.get("signal_id", "")
        target_workspace_id = entity.get("target_workspace_id", "")
        task = entity.get("task", "")
        if signal_id and target_workspace_id and task:
            return {
                "type": "handoff_signal",
                "signal_id": signal_id,
                "target_workspace_id": target_workspace_id,
                "task": task,
            }
    return None


def clear_memory_for_tests() -> None:
    """Test helper — wipe in-process memory buckets."""
    _TURN_MEMORY.clear()
    _ENTITY_MEMORY.clear()


__all__ = [
    "clear_memory_for_tests",
    "entity_context",
    "note_briefing_surface_offer",
    "recent_turns",
    "remember_entities",
    "remember_top_signal",
    "remember_turn",
    "resolve_followup_action",
    "session_key",
]
