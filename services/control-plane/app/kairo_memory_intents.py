"""Explicit remember/recall intents for operator conversation."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from app.kairo_participant_memory import apply_participant_address
from app.persistence.operator_memory_store import create_memory, search_memories

_REMEMBER_THIS_RE = re.compile(
    r"^(?:remember this|remember that|make a note|note this)\s*[:,-]?\s+(.+)$",
    re.IGNORECASE,
)
_RECALL_NOTE_RE = re.compile(
    r"^(?:what did i note about|what did i remember about|what do my notes say about)\s+(.+?)\??$",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _memory_artifact(item: dict[str, Any]) -> dict[str, object]:
    return {
        "artifact_id": str(item.get("memory_id") or ""),
        "title": str(item.get("title") or "Operator memory"),
        "summary": str(item.get("content") or "")[:160],
        "body": str(item.get("content") or ""),
        "sources": [
            {
                "label": str(source.get("label") or source.get("ref_type") or "source"),
                "detail": str(source.get("ref_id") or ""),
            }
            for source in item.get("source_refs", [])
            if isinstance(source, dict)
        ],
        "actions": [],
    }


def maybe_handle_memory_intent(
    *,
    content: str,
    session_id: str,
    workspace_id: str | None,
    guest_name: str | None,
) -> dict[str, object] | None:
    remember_match = _REMEMBER_THIS_RE.match(content)
    if remember_match:
        note = remember_match.group(1).strip()
        if not note:
            return None
        scoped_workspace_id = str(workspace_id or "").strip()
        memory = create_memory(
            workspace_id=scoped_workspace_id,
            scope="workspace" if scoped_workspace_id else "personal",
            kind="note",
            title=note[:72],
            content=note,
            source_refs=[
                {
                    "ref_type": "conversation",
                    "ref_id": session_id,
                    "label": "Operator conversation",
                    "workspace_id": scoped_workspace_id,
                }
            ],
            created_at=_utc_now(),
        )
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                "Confirmed. I've saved that as a cited operator memory.",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [_memory_artifact(memory)],
        }

    recall_match = _RECALL_NOTE_RE.match(content)
    if not recall_match:
        return None
    query = recall_match.group(1).strip()
    matches = search_memories(query, workspace_id=str(workspace_id or "").strip() or None, limit=2)
    if matches:
        first = matches[0]
        reply = apply_participant_address(
            f"I found {len(matches)} note{'s' if len(matches) != 1 else ''}. Top match: "
            f"{first.get('title')}: {first.get('content')}",
            guest_name,
        )
    else:
        reply = apply_participant_address(
            "I couldn't find a matching operator note yet.",
            guest_name,
        )
    return {
        "turn_kind": "status_question",
        "reply": reply,
        "source": "template",
        "command_content": None,
        "action": None,
        "artifacts": [_memory_artifact(item) for item in matches],
    }

