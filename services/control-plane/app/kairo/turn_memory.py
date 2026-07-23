"""Session-scoped turn and entity memory for KAIRO follow-ups (OP-C5, M2)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.persistence.kairo_session_memory_store import (
    delete_all_session_memory_for_tests as _delete_all_session_memory_for_tests,
    load_session_memory as _load_session_memory,
    save_session_memory as _save_session_memory,
)

_MAX_TURN_MEMORY = 8

_TURN_MEMORY: dict[str, list[dict[str, str]]] = {}
_ENTITY_MEMORY: dict[str, dict[str, str]] = {}
_LOADED_KEYS: set[str] = set()

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


def _ensure_hydrated(session_id: str) -> None:
    key = session_key(session_id)
    if key in _LOADED_KEYS:
        return
    _LOADED_KEYS.add(key)
    loaded = _load_session_memory(key)
    if loaded is None:
        return
    turns, entities = loaded
    if turns:
        _TURN_MEMORY[key] = turns[-_MAX_TURN_MEMORY:]
    if entities:
        _ENTITY_MEMORY[key] = entities


def _persist(session_id: str) -> None:
    key = session_key(session_id)
    _save_session_memory(
        key,
        _TURN_MEMORY.get(key, []),
        _ENTITY_MEMORY.get(key, {}),
    )


def remember_turn(session_id: str, role: str, content: str) -> None:
    _ensure_hydrated(session_id)
    key = session_key(session_id)
    bucket = _TURN_MEMORY.setdefault(key, [])
    bucket.append({"role": role, "content": content.strip()})
    if len(bucket) > _MAX_TURN_MEMORY:
        del bucket[: len(bucket) - _MAX_TURN_MEMORY]
    _persist(session_id)


def recent_turns(session_id: str) -> list[dict[str, str]]:
    _ensure_hydrated(session_id)
    return list(_TURN_MEMORY.get(session_key(session_id), []))


def remember_entities(session_id: str, **fields: str) -> None:
    _ensure_hydrated(session_id)
    key = session_key(session_id)
    bucket = _ENTITY_MEMORY.setdefault(key, {})
    for name, value in fields.items():
        cleaned = str(value or "").strip()
        if cleaned:
            bucket[name] = cleaned
        elif name in bucket:
            del bucket[name]
    _persist(session_id)


def entity_context(session_id: str) -> dict[str, str]:
    _ensure_hydrated(session_id)
    return dict(_ENTITY_MEMORY.get(session_key(session_id), {}))


def build_lane_b_memory_appendix(session_id: str, *, max_chars: int = 800) -> str:
    from app.kairo.mission_memory import mission_memory_appendix

    entity = entity_context(session_id)
    turns = recent_turns(session_id)
    lines: list[str] = []
    mission_block = mission_memory_appendix(session_id, max_chars=min(400, max_chars))
    if mission_block:
        lines.append(mission_block)
    if entity:
        lines.append("KAIRO memory (non-authoritative):")
        if entity.get("target_workspace_id"):
            lines.append(f"- Workspace: {entity['target_workspace_id']}")
        if entity.get("signal_title"):
            lines.append(f"- Signal: {entity['signal_title']}")
        elif entity.get("signal_id"):
            lines.append(f"- Signal id: {entity['signal_id']}")
        if entity.get("task"):
            lines.append(f"- Task: {entity['task']}")
    if turns:
        if lines:
            lines.append("")
        lines.append("Recent KAIRO turns:")
        for turn in turns[-4:]:
            role = str(turn.get("role") or "unknown").strip() or "unknown"
            content = " ".join(str(turn.get("content") or "").strip().split())
            if content:
                lines.append(f"- {role}: {content}")
    appendix = "\n".join(lines).strip()
    if not appendix:
        return ""
    if len(appendix) <= max_chars:
        return appendix
    return appendix[: max(0, max_chars - 1)].rstrip() + "…"


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


def clear_memory_cache_for_tests() -> None:
    """Simulate control-plane restart — drop in-process cache only."""
    _TURN_MEMORY.clear()
    _ENTITY_MEMORY.clear()
    _LOADED_KEYS.clear()


def clear_memory_for_tests() -> None:
    """Test helper — wipe in-process and persisted memory buckets."""
    clear_memory_cache_for_tests()
    _delete_all_session_memory_for_tests()


__all__ = [
    "build_lane_b_memory_appendix",
    "clear_memory_cache_for_tests",
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
