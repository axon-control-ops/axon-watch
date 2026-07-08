"""Grounded KAIRO conversation turns for operator galaxy dialogue (OP-C1)."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from app.chat.command_intent import (
    classify_command,
    command_display_name,
    expand_command_shortcuts,
    is_question,
)
from app.kairo_conversation_reply import (
    compose_conversation_reply,
    compose_smalltalk_reply,
    is_open_style_question,
)
from app.operator_briefing import build_operator_briefing
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_fleet_health import build_operator_fleet_health

ConversationTurnKind = Literal["status_question", "open_question", "command", "chat", "action"]
ConversationSource = Literal["template", "model", "fallback"]

_MAX_TURN_MEMORY = 8

_STATUS_HINT_RE = re.compile(
    r"\b("
    r"approval|approvals|attention|on fire|status|briefing|fleet|health|"
    r"signal|signals|running|active run|what needs|what's wrong|what is wrong|"
    r"happening|nominal|degraded|waiting|clear"
    r")\b",
    re.IGNORECASE,
)
_HANDOFF_ACTION_RE = re.compile(
    r"\b(hand\s*it\s*off|hand\s*off|handoff|continue in ide|investigate in ide|open in ide)\b",
    re.IGNORECASE,
)
_CONFIRM_RE = re.compile(r"^(yes|yeah|yep|do it|confirm|go ahead)\.?$", re.IGNORECASE)

_TURN_MEMORY: dict[str, list[dict[str, str]]] = {}
_ENTITY_MEMORY: dict[str, dict[str, str]] = {}


def _session_key(session_id: str) -> str:
    cleaned = str(session_id or "default").strip() or "default"
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


def _remember_turn(session_id: str, role: str, content: str) -> None:
    key = _session_key(session_id)
    bucket = _TURN_MEMORY.setdefault(key, [])
    bucket.append({"role": role, "content": content.strip()})
    if len(bucket) > _MAX_TURN_MEMORY:
        del bucket[: len(bucket) - _MAX_TURN_MEMORY]


def _recent_turns(session_id: str) -> list[dict[str, str]]:
    return list(_TURN_MEMORY.get(_session_key(session_id), []))


def _remember_entities(session_id: str, **fields: str) -> None:
    key = _session_key(session_id)
    bucket = _ENTITY_MEMORY.setdefault(key, {})
    for name, value in fields.items():
        cleaned = str(value or "").strip()
        if cleaned:
            bucket[name] = cleaned


def _entity_context(session_id: str) -> dict[str, str]:
    return dict(_ENTITY_MEMORY.get(_session_key(session_id), {}))


def _remember_top_signal(session_id: str, pack: dict[str, Any]) -> None:
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
    workspace_id = str(signal.get("workspace_id", "")).strip()
    title = str(signal.get("title", "")).strip()
    summary = str(signal.get("summary", "")).strip()
    task = f'Investigate signal "{title}"'
    if summary:
        task = f'{task}: {summary}'
    _remember_entities(
        session_id,
        signal_id=signal_id,
        target_workspace_id=workspace_id,
        signal_title=title,
        task=task,
    )


def _resolve_followup_action(content: str, session_id: str) -> dict[str, object] | None:
    trimmed = content.strip()
    entity = _entity_context(session_id)
    if _CONFIRM_RE.match(trimmed):
        pending_command = entity.get("pending_command", "")
        if pending_command:
            return {"type": "dispatch_command", "content": pending_command}
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


def build_conversation_context_pack(*, workspace_id: str | None = None) -> dict[str, Any]:
    scoped = workspace_id.strip() if workspace_id else None
    briefing = build_operator_briefing(workspace_id=scoped)
    fleet = build_operator_fleet_health()
    graph = build_operator_brain_graph()
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    critical_workspaces = sum(
        1
        for item in fleet.get("items", [])
        if isinstance(item, dict) and item.get("tone") == "critical"
    )
    attention_workspaces = sum(
        1
        for item in fleet.get("items", [])
        if isinstance(item, dict) and item.get("tone") == "attention"
    )
    return {
        "briefing": briefing,
        "fleet": {
            "workspace_count": len(fleet.get("items", [])),
            "critical_count": critical_workspaces,
            "attention_count": attention_workspaces,
        },
        "graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }


def classify_conversation_turn(content: str) -> ConversationTurnKind:
    trimmed = content.strip()
    if not trimmed:
        return "chat"
    normalized = expand_command_shortcuts(trimmed)
    intent = classify_command(normalized)
    if intent != "unsupported":
        return "command"
    if is_open_style_question(trimmed):
        return "open_question"
    if _STATUS_HINT_RE.search(trimmed):
        return "status_question"
    if is_question(trimmed):
        return "open_question"
    return "chat"



def answer_status_question(content: str, pack: dict[str, Any]) -> str:
    return compose_conversation_reply(
        content=content,
        pack=pack,
        session_id="static",
        recent_turns=[],
    )


def _command_ack_line(content: str) -> str:
    normalized = expand_command_shortcuts(content.strip())
    intent = classify_command(normalized)
    label = command_display_name(normalized)
    if intent == "git_status":
        return "Right — I'll pull git status now."
    if intent == "health_probe":
        return "Running a health check now."
    if intent == "list_files":
        return "Listing workspace files for you."
    if intent == "read_file":
        return f"Reading {label.replace('Read ', '')}."
    if intent == "shell_command":
        return f"On it — {label}."
    if intent == "resume_from_review":
        return "Resuming from review."
    return f"Understood — {label}."


def converse_turn(
    *,
    content: str,
    session_id: str = "default",
    workspace_id: str | None = None,
    use_runtime: bool = False,
) -> dict[str, object]:
    trimmed = content.strip()
    if not trimmed:
        raise ValueError("content must not be empty")

    pack = build_conversation_context_pack(workspace_id=workspace_id)
    followup = _resolve_followup_action(trimmed, session_id)
    if followup:
        action_type = str(followup.get("type", ""))
        if action_type == "handoff_signal":
            reply = "Handing this off to the IDE now."
            _remember_turn(session_id, "user", trimmed)
            _remember_turn(session_id, "assistant", reply)
            return {
                "turn_kind": "action",
                "reply": reply,
                "source": "template",
                "command_content": None,
                "action": followup,
            }
        if action_type == "dispatch_command":
            command_content = str(followup.get("content", "")).strip()
            reply = _command_ack_line(command_content)
            _remember_entities(session_id, pending_command="")
            _remember_turn(session_id, "user", trimmed)
            _remember_turn(session_id, "assistant", reply)
            return {
                "turn_kind": "action",
                "reply": reply,
                "source": "template",
                "command_content": command_content,
                "action": followup,
            }

    turn_kind = classify_conversation_turn(trimmed)
    source: ConversationSource = "template"
    reply = ""
    command_content: str | None = None

    if turn_kind == "command":
        normalized = expand_command_shortcuts(trimmed)
        command_content = normalized
        reply = _command_ack_line(normalized)
        source = "template"
        _remember_entities(session_id, pending_command=normalized)
    elif turn_kind == "status_question":
        recent = _recent_turns(session_id)
        reply = compose_conversation_reply(
            content=trimmed,
            pack=pack,
            session_id=session_id,
            recent_turns=recent,
        )
        source = "template"
        _remember_top_signal(session_id, pack)
    else:
        recent = _recent_turns(session_id)
        smalltalk = compose_smalltalk_reply(
            content=trimmed,
            session_id=session_id,
            recent_turns=recent,
        )
        if smalltalk:
            reply = smalltalk
            source = "template"
        else:
            reply = compose_conversation_reply(
                content=trimmed,
                pack=pack,
                session_id=session_id,
                recent_turns=recent,
            )
            source = "template"

    _remember_turn(session_id, "user", trimmed)
    _remember_turn(session_id, "assistant", reply)

    return {
        "turn_kind": turn_kind,
        "reply": reply,
        "source": source,
        "command_content": command_content,
        "action": None,
    }


__all__ = [
    "answer_status_question",
    "build_conversation_context_pack",
    "classify_conversation_turn",
    "converse_turn",
]
