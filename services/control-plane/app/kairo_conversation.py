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
from app.kairo_voice import generate_spoken_line
from app.operator_briefing import build_operator_briefing
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_fleet_health import build_operator_fleet_health
from app.persistence import operator_presence_settings_store

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
    if is_question(trimmed) or _STATUS_HINT_RE.search(trimmed):
        return "status_question"
    if is_question(trimmed):
        return "open_question"
    return "chat"


def _answer_approvals(pending: int) -> str:
    if pending <= 0:
        return "No pending approvals — you're clear to proceed."
    suffix = "" if pending == 1 else "s"
    return f"You have {pending} approval{suffix} waiting — open Attention to review."


def _answer_attention(*, pending: int, top_signal_title: str, active_run_count: int) -> str:
    parts: list[str] = []
    if pending > 0:
        suffix = "" if pending == 1 else "s"
        parts.append(f"{pending} approval{suffix} need you first")
    if top_signal_title:
        parts.append(f"top signal is {top_signal_title}")
    elif active_run_count > 0:
        suffix = "" if active_run_count == 1 else "s"
        parts.append(f"{active_run_count} active run{suffix} in flight")
    if not parts:
        return "Nothing urgent — fleet looks nominal from here."
    return f"Here's what needs you: {'; '.join(parts)}."


def answer_status_question(content: str, pack: dict[str, Any]) -> str:
    briefing = pack["briefing"]
    lower = content.lower()
    pending = int(briefing.get("pending_approvals", {}).get("count", 0))
    notice = str(briefing.get("notice") or "").strip()
    advise = str(briefing.get("advise") or "").strip()
    top_signals = [
        item for item in briefing.get("top_signals", []) if isinstance(item, dict)
    ]
    top_signal_title = str(top_signals[0].get("title", "")).strip() if top_signals else ""
    active_runs = [
        item for item in briefing.get("active_runs", []) if isinstance(item, dict)
    ]
    degraded = bool(briefing.get("degraded", {}).get("active"))

    if "approval" in lower:
        return _answer_approvals(pending)
    if any(token in lower for token in ("on fire", "attention", "wrong", "needs")):
        return _answer_attention(
            pending=pending,
            top_signal_title=top_signal_title,
            active_run_count=len(active_runs),
        )
    if "fleet" in lower or "health" in lower:
        fleet = pack["fleet"]
        critical = int(fleet.get("critical_count", 0))
        attention = int(fleet.get("attention_count", 0))
        workspace_count = int(fleet.get("workspace_count", 0))
        if critical > 0:
            suffix = "" if critical == 1 else "s"
            return (
                f"Fleet scan: {critical} workspace{suffix} in critical state "
                f"across {workspace_count} bound."
            )
        if attention > 0:
            suffix = "" if attention == 1 else "s"
            return (
                f"Fleet scan: {attention} workspace{suffix} need attention; "
                "no critical fires right now."
            )
        suffix = "" if workspace_count == 1 else "s"
        return f"Fleet nominal — {workspace_count} workspace{suffix} look healthy."
    if degraded:
        return "Runtime is degraded — check connectivity before dispatching more work."
    if notice and advise:
        return f"{notice} {advise}"
    if notice:
        return notice
    if advise:
        return advise
    return "Systems nominal — standing by for your next command."


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

    settings = operator_presence_settings_store.load_settings()
    persona_enabled = bool(settings.get("operator_persona_enabled", True))
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
        reply = answer_status_question(trimmed, pack)
        source = "template"
        _remember_top_signal(session_id, pack)
    else:
        briefing = pack["briefing"]
        context = {
            "notice": briefing.get("notice"),
            "advise": briefing.get("advise"),
            "pending_approvals": briefing.get("pending_approvals", {}).get("count", 0),
            "top_signal_title": (
                str(briefing.get("top_signals", [{}])[0].get("title", ""))
                if briefing.get("top_signals")
                else ""
            ),
            "operator_prompt": trimmed,
            "recent_turns": _recent_turns(session_id)[-4:],
        }
        spoken = generate_spoken_line(
            event_type="briefing" if turn_kind == "open_question" else "chat_summary",
            context=context,
            session_id=session_id,
            persona_enabled=persona_enabled,
            narration="minimal",
            workspace_id=str(workspace_id or ""),
            use_runtime=use_runtime and turn_kind == "open_question",
        )
        reply = str(spoken.get("line") or "").strip()
        spoken_source = str(spoken.get("source") or "fallback")
        source = "model" if spoken_source == "model" else "fallback"
        if not reply:
            reply = answer_status_question(trimmed, pack)
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
