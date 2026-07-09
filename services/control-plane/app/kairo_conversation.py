"""Grounded KAIRO conversation turns for operator galaxy dialogue (OP-C1)."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Literal

from app.chat.command_intent import (
    classify_command,
    command_display_name,
    command_requires_confirmation,
    expand_command_shortcuts,
    is_question,
    is_auto_complete_run_summary,
)
from app.chat.lane_b_agent import LaneBContext, build_lane_b_context_block
from app.cli_runtime.router import dispatch_ide_composer
from app.kairo_conversation_reply import (
    build_conversation_facts,
    compose_conversation_reply,
    compose_smalltalk_reply,
    is_open_style_question,
)
from app.kairo_voice import normalize_spoken_line
from app.operator_briefing import build_operator_briefing
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_fleet_health import build_operator_fleet_health
from app.operator_persona_name import OPERATOR_PERSONA_BACKRONYM, OPERATOR_PERSONA_NAME
from app.operator_persona_stt_aliases import normalize_persona_stt_aliases
from app.persistence.voice_transcript_store import append_voice_transcript
from app.workspace_project_bindings import get_workspace_project_binding, load_workspace_project_bindings

ConversationTurnKind = Literal["status_question", "open_question", "command", "chat", "action"]
ConversationSource = Literal["template", "model", "fallback"]
ConversationAnswerTier = Literal["fast", "deep"]

_MAX_RUNTIME_VOICE_REPLY_CHARS = 1200
_MAX_TURN_MEMORY = 8

_OPEN_DETAIL_RE = re.compile(
    r"\b(walk me through|explain|tell me about|in detail|step by step|compare|tradeoffs?|everything)\b",
    re.IGNORECASE,
)

_STATUS_HINT_RE = re.compile(
    r"\b("
    r"approval|approvals|attention|on fire|status|briefing|fleet|health|"
    r"signal|signals|running|active run|what needs|what's wrong|what is wrong|"
    r"happening|nominal|degraded|waiting|clear"
    r")\b",
    re.IGNORECASE,
)
_WORKSPACE_ACTIVITY_RE = re.compile(
    r"(?:\b(check|show|tell me|what|pull up)\b[\w\s,-]*)?"
    r"\b(workspace|dashpro|axon[\s-]*watch|axon[\s-]*local)\b"
    r"[\w\s,-]*\b(check|show|what|pull up)?\b[\w\s,-]*"
    r"\b(just did|doing|latest|recent|activity)\b",
    re.IGNORECASE,
)
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

_TURN_MEMORY: dict[str, list[dict[str, str]]] = {}
_ENTITY_MEMORY: dict[str, dict[str, str]] = {}


def _normalize_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _workspace_aliases(workspace_id: str, display_name: str | None) -> set[str]:
    aliases = {_normalize_alias(workspace_id.replace("workspace_", ""))}
    if display_name:
        aliases.add(_normalize_alias(display_name))
    if workspace_id == "workspace_dashpro":
        aliases.update(
            {
                "dashpro",
                "dash pro",
                "best pro",
                "this pro",
                "probox space",
                "dashpro workspace",
            }
        )
    return {alias for alias in aliases if alias}


def _infer_workspace_id_from_content(content: str) -> str | None:
    normalized = _normalize_alias(content)
    if not normalized:
        return None
    bindings = load_workspace_project_bindings()
    matches: list[tuple[str, str]] = []
    for binding in bindings.values():
        for alias in _workspace_aliases(binding.workspace_id, binding.display_name):
            if alias and alias in normalized:
                matches.append((binding.workspace_id, alias))
    if matches:
        matches.sort(key=lambda item: len(item[1]), reverse=True)
        return matches[0][0]
    if "pro workspace" in normalized or "probox space" in normalized:
        return "workspace_dashpro"
    return None


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


def _note_briefing_surface_offer(session_id: str, reply: str) -> None:
    if _BRIEFING_SURFACE_OFFER_RE.search(str(reply or "")):
        _remember_entities(session_id, pending_briefing_surface="1")


def _resolve_followup_action(content: str, session_id: str) -> dict[str, object] | None:
    trimmed = content.strip()
    entity = _entity_context(session_id)
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


def _runtime_workspace_id(*, workspace_id: str | None, pack: dict[str, Any]) -> str:
    scoped = str(workspace_id or "").strip()
    if scoped:
        return scoped

    briefing = pack.get("briefing", {})
    scope = briefing.get("scope", {}) if isinstance(briefing, dict) else {}
    scoped_from_briefing = str(scope.get("workspace_id") or "").strip()
    if scoped_from_briefing:
        return scoped_from_briefing

    top_signals = briefing.get("top_signals", []) if isinstance(briefing, dict) else []
    if top_signals and isinstance(top_signals[0], dict):
        top_signal_workspace = str(top_signals[0].get("workspace_id") or "").strip()
        if top_signal_workspace:
            return top_signal_workspace

    return "workspace_axon_watch"


def _build_runtime_context_block(
    *,
    content: str,
    workspace_id: str,
    pack: dict[str, Any],
    session_id: str,
    recent_turns: list[dict[str, str]],
    context_node_id: str | None = None,
    context_signal_id: str | None = None,
) -> str:
    facts = build_conversation_facts(pack)
    base = build_lane_b_context_block(
        LaneBContext(
            workspace_id=workspace_id,
            composer_mode="ask",
        )
    )
    recent_lines = [
        f'{turn.get("role", "unknown")}: {str(turn.get("content") or "").strip()}'
        for turn in recent_turns[-6:]
        if str(turn.get("content") or "").strip()
    ]
    extras = [
        "Operator voice assistant contract (JARVIS-style):",
        f"- You are {OPERATOR_PERSONA_NAME} ({OPERATOR_PERSONA_BACKRONYM}) — dry, impeccably polite, confident.",
        "- Razor wit when it fits; never sycophantic or chatbot-cheerful.",
        '- No "sir", "madam", or honorifics unless the operator used one.',
        "- First person, natural spoken language; ground answers in operator state and workspace context.",
        "- No markdown, bullets, code fences, or raw path dumps unless the operator asked for implementation detail.",
        (
            "- For walkthrough, explain, compare, or in-detail requests: use 3-6 short paragraphs."
            if _OPEN_DETAIL_RE.search(content)
            else "- For quick questions: 1-3 short sentences."
        ),
        f"Voice session: {session_id}",
        f"Pending approvals: {facts['pending_approvals']}",
        f"Top signal: {facts['top_signal_title'] or 'none'}",
        f"Top signal summary: {facts['top_signal_summary'] or 'none'}",
        f"Active runs: {facts['active_run_count']}",
        f"Primary run: {facts['primary_run_summary'] or 'none'}",
        f"Degraded active: {'yes' if facts['degraded'] else 'no'}",
        f"CLI dispatch ready: {'yes' if facts['cli_dispatch_ready'] else 'no'}",
        f"CLI blockers: {'; '.join(facts['cli_blockers']) or 'none'}",
        f"Notice: {facts['notice'] or 'none'}",
        f"Advise: {facts['advise'] or 'none'}",
    ]
    if context_node_id:
        extras.append(f"Focused brain node: {context_node_id}")
    if context_signal_id:
        extras.append(f"Focused signal: {context_signal_id}")
    if recent_lines:
        extras.append("Recent conversation:")
        extras.extend(recent_lines)
    return f"{base}\n\n" + "\n".join(extras)


def _should_use_runtime_for_open_question(
    *,
    content: str,
    use_runtime: bool,
    answer_tier: ConversationAnswerTier,
) -> bool:
    if not use_runtime:
        return False
    if answer_tier == "deep":
        return True
    return bool(_OPEN_DETAIL_RE.search(content))


def _short_reply_summary(reply: str, *, max_chars: int = 280) -> str:
    trimmed = re.sub(r"\s+", " ", reply.strip())
    if not trimmed:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", trimmed)
    summary = ""
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        next_summary = f"{summary} {candidate}".strip()
        if len(next_summary) > max_chars:
            break
        summary = next_summary
        if summary.count(".") + summary.count("!") + summary.count("?") >= 2:
            break
    if summary:
        return summary
    if len(trimmed) <= max_chars:
        return trimmed
    shortened = trimmed[: max_chars - 1].rstrip(" ,;:")
    return f"{shortened}…"


def _artifact_handoff_action(
    *,
    pack: dict[str, Any],
    signal_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, object] | None:
    briefing = pack.get("briefing", {})
    top_signals = [
        item for item in briefing.get("top_signals", []) if isinstance(item, dict)
    ]
    signal: dict[str, Any] | None = None
    if signal_id:
        for candidate in top_signals:
            if str(candidate.get("signal_id", "")).strip() == signal_id:
                signal = candidate
                break
    if signal is None and top_signals:
        signal = top_signals[0]
    if signal is None:
        resolved_workspace_id = str(workspace_id or "").strip()
        resolved_signal_id = str(signal_id or "").strip()
        if not resolved_workspace_id or not resolved_signal_id:
            return None
        task = f"Investigate signal {resolved_signal_id}"
        return {
            "type": "handoff_ide",
            "signal_id": resolved_signal_id,
            "target_workspace_id": resolved_workspace_id,
            "task": task,
        }
    resolved_workspace_id = (
        str(workspace_id or signal.get("workspace_id") or "").strip() or None
    )
    resolved_signal_id = str(signal.get("signal_id") or "").strip()
    title = str(signal.get("title") or "signal").strip()
    summary = str(signal.get("summary") or "").strip()
    if not resolved_workspace_id or not resolved_signal_id:
        return None
    task = f'Investigate signal "{title}"'
    if summary:
        task = f"{task}: {summary}"
    return {
        "type": "handoff_ide",
        "signal_id": resolved_signal_id,
        "target_workspace_id": resolved_workspace_id,
        "task": task,
    }


def _build_runtime_artifact(
    *,
    content: str,
    reply: str,
    pack: dict[str, Any],
    signal_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, object]:
    facts = build_conversation_facts(pack)
    artifact_id = f"artifact_{hashlib.sha256((content + reply).encode('utf-8')).hexdigest()[:12]}"
    summary = _short_reply_summary(reply)
    title = facts["top_signal_title"] or "VAXON analysis"
    sources: list[dict[str, str]] = []
    if facts["top_signal_title"]:
        detail = facts["top_signal_summary"] or facts["top_signal_title"]
        sources.append({"label": "Top signal", "detail": detail})
    if facts["notice"]:
        sources.append({"label": "Briefing notice", "detail": facts["notice"]})
    if facts["advise"]:
        sources.append({"label": "Briefing advise", "detail": facts["advise"]})
    if not sources:
        sources.append({"label": "Operator briefing", "detail": "Grounded in current fleet and run state."})
    actions: list[dict[str, object]] = []
    handoff = _artifact_handoff_action(
        pack=pack,
        signal_id=signal_id,
        workspace_id=workspace_id,
    )
    if handoff:
        actions.append({"label": "Continue in IDE", "ui_action": handoff})
    return {
        "artifact_id": artifact_id,
        "title": title,
        "summary": summary or "Analysis ready.",
        "body": reply,
        "sources": sources,
        "actions": actions,
    }


def _runtime_assistant_reply(
    *,
    content: str,
    session_id: str,
    workspace_id: str | None,
    pack: dict[str, Any],
    recent_turns: list[dict[str, str]],
    context_node_id: str | None = None,
    context_signal_id: str | None = None,
) -> tuple[str, ConversationSource]:
    resolved_workspace_id = _runtime_workspace_id(workspace_id=workspace_id, pack=pack)
    context_block = _build_runtime_context_block(
        content=content,
        workspace_id=resolved_workspace_id,
        pack=pack,
        session_id=session_id,
        recent_turns=recent_turns,
        context_node_id=context_node_id,
        context_signal_id=context_signal_id,
    )
    payload = dispatch_ide_composer(
        workspace_id=resolved_workspace_id,
        composer_mode="ask",
        user_prompt=content,
        context_block=context_block,
        execution_access="consultative",
    )
    reply = normalize_spoken_line(
        str(payload.get("content") or ""),
        max_chars=_MAX_RUNTIME_VOICE_REPLY_CHARS,
    )
    if not reply:
        return (
            compose_conversation_reply(
                content=content,
                pack=pack,
                session_id=session_id,
                recent_turns=recent_turns,
            ),
            "fallback",
        )
    return reply, ("model" if bool(payload.get("dispatched")) else "fallback")


def build_conversation_context_pack(*, workspace_id: str | None = None) -> dict[str, Any]:
    scoped = workspace_id.strip() if workspace_id else None
    briefing = build_operator_briefing(workspace_id=scoped)
    fleet = build_operator_fleet_health()
    graph = build_operator_brain_graph()
    binding = get_workspace_project_binding(scoped) if scoped else None
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
        "workspace": {
            "workspace_id": scoped or str(briefing.get("scope", {}).get("workspace_id") or "").strip(),
            "display_name": (
                str(briefing.get("scope", {}).get("display_name") or "").strip()
                or str(binding.display_name if binding else "").strip()
            ),
        },
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
    if _WORKSPACE_ACTIVITY_RE.search(trimmed):
        return "status_question"
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


def _workspace_short_label(pack: dict[str, Any]) -> str | None:
    workspace = pack.get("workspace")
    if not isinstance(workspace, dict):
        return None
    label = str(workspace.get("display_name") or workspace.get("workspace_id") or "").strip()
    return label or None


def _command_ack_line(content: str, *, workspace_label: str | None = None) -> str:
    normalized = expand_command_shortcuts(content.strip())
    intent = classify_command(normalized)
    label = command_display_name(normalized)
    scope = f" for {workspace_label}" if workspace_label else ""
    auto_complete_hint = (
        " It should auto-complete once the output lands."
        if is_auto_complete_run_summary(label)
        else ""
    )
    if intent == "git_status":
        return (
            f"On it — running git status{scope}. "
            "I'll read branch and working tree, then put the full output in Command Results."
            f"{auto_complete_hint}"
        )
    if intent == "health_probe":
        return (
            f"Running a health probe{scope} now — "
            f"checking connectors, runtime, and service reachability.{auto_complete_hint}"
        )
    if intent == "list_files":
        return f"Listing workspace files{scope} — results will appear in Command Results.{auto_complete_hint}"
    if intent == "read_file":
        target = label.replace("Read ", "").strip()
        return (
            f"Opening {target or 'that file'} now — I'll surface the contents in Command Results."
            f"{auto_complete_hint}"
        )
    if intent == "shell_command":
        return (
            f"I can run {label}{scope}. "
            "Say yes when you want me to dispatch it — output will land in Command Results."
        )
    if intent == "resume_from_review":
        return (
            "I can resume from review and pick up where we left off. "
            "Say yes when you want me to continue."
        )
    if command_requires_confirmation(normalized):
        return (
            f"I can run {label}{scope}. "
            "Say yes when you want me to dispatch it — output will land in Command Results."
        )
    return f"Understood — {label}. I'll report back in Command Results."


def _log_voice_turn(
    *,
    session_id: str,
    workspace_id: str | None,
    raw_content: str,
    normalized_content: str,
    payload: dict[str, object],
    duration_ms: int | None = None,
    runtime_dispatched: bool = False,
) -> dict[str, object]:
    try:
        stt_note = None
        if raw_content.strip().lower() != normalized_content.strip().lower():
            stt_note = "stt_normalized"
        append_voice_transcript(
            session_id=session_id,
            workspace_id=workspace_id,
            raw_content=raw_content,
            normalized_content=normalized_content,
            reply=str(payload.get("reply") or ""),
            turn_kind=str(payload.get("turn_kind") or "unknown"),
            source=str(payload.get("source") or "unknown"),
            stt_note=stt_note,
            duration_ms=duration_ms,
            runtime_dispatched=runtime_dispatched,
        )
    except Exception:
        pass
    return payload


def converse_turn(
    *,
    content: str,
    session_id: str = "default",
    workspace_id: str | None = None,
    use_runtime: bool = False,
    answer_tier: str = "fast",
    context_workspace_id: str | None = None,
    context_signal_id: str | None = None,
    context_node_id: str | None = None,
) -> dict[str, object]:
    started_at = time.perf_counter()
    raw_content = content.strip()
    trimmed = normalize_persona_stt_aliases(raw_content)
    if not trimmed:
        raise ValueError("content must not be empty")

    tier: ConversationAnswerTier = "deep" if str(answer_tier).strip().lower() == "deep" else "fast"
    inferred_workspace_id = _infer_workspace_id_from_content(trimmed)
    resolved_workspace_id = context_workspace_id or workspace_id or inferred_workspace_id
    pack = build_conversation_context_pack(workspace_id=resolved_workspace_id)
    if context_signal_id and resolved_workspace_id:
        _remember_entities(
            session_id,
            signal_id=context_signal_id,
            target_workspace_id=resolved_workspace_id,
            task=f"Investigate signal {context_signal_id}",
        )
    followup = _resolve_followup_action(trimmed, session_id)
    if followup:
        action_type = str(followup.get("type", ""))
        if action_type == "handoff_signal":
            reply = "Handing this off to the IDE now."
            _remember_turn(session_id, "user", trimmed)
            _remember_turn(session_id, "assistant", reply)
            return _log_voice_turn(
                session_id=session_id,
                workspace_id=workspace_id,
                raw_content=raw_content,
                normalized_content=trimmed,
                payload={
                    "turn_kind": "action",
                    "reply": reply,
                    "source": "template",
                    "command_content": None,
                    "action": followup,
                    "artifacts": [],
                },
                duration_ms=round((time.perf_counter() - started_at) * 1000),
            )
        if action_type == "dispatch_command":
            command_content = str(followup.get("content", "")).strip()
            reply = _command_ack_line(
                command_content,
                workspace_label=_workspace_short_label(pack),
            )
            _remember_entities(session_id, pending_command="")
            _remember_turn(session_id, "user", trimmed)
            _remember_turn(session_id, "assistant", reply)
            return _log_voice_turn(
                session_id=session_id,
                workspace_id=workspace_id,
                raw_content=raw_content,
                normalized_content=trimmed,
                payload={
                    "turn_kind": "action",
                    "reply": reply,
                    "source": "template",
                    "command_content": command_content,
                    "action": followup,
                    "artifacts": [],
                },
                duration_ms=round((time.perf_counter() - started_at) * 1000),
            )
        if action_type == "focus_briefing":
            reply = "Opening the briefing for you."
            _remember_entities(session_id, pending_briefing_surface="")
            _remember_turn(session_id, "user", trimmed)
            _remember_turn(session_id, "assistant", reply)
            return _log_voice_turn(
                session_id=session_id,
                workspace_id=workspace_id,
                raw_content=raw_content,
                normalized_content=trimmed,
                payload={
                    "turn_kind": "action",
                    "reply": reply,
                    "source": "template",
                    "command_content": None,
                    "action": followup,
                    "artifacts": [],
                },
                duration_ms=round((time.perf_counter() - started_at) * 1000),
            )

    turn_kind = classify_conversation_turn(trimmed)
    source: ConversationSource = "template"
    reply = ""
    command_content: str | None = None
    artifacts: list[dict[str, object]] = []
    runtime_dispatched = False

    requires_confirmation = False
    if turn_kind == "command":
        normalized = expand_command_shortcuts(trimmed)
        command_content = normalized
        requires_confirmation = command_requires_confirmation(normalized)
        reply = _command_ack_line(normalized, workspace_label=_workspace_short_label(pack))
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
    elif turn_kind == "open_question" and _should_use_runtime_for_open_question(
        content=trimmed,
        use_runtime=use_runtime,
        answer_tier=tier,
    ):
        recent = _recent_turns(session_id)
        runtime_reply, source = _runtime_assistant_reply(
            content=trimmed,
            session_id=session_id,
            workspace_id=resolved_workspace_id,
            pack=pack,
            recent_turns=recent,
            context_node_id=context_node_id,
            context_signal_id=context_signal_id,
        )
        runtime_dispatched = source == "model"
        artifacts = [
            _build_runtime_artifact(
                content=trimmed,
                reply=runtime_reply,
                pack=pack,
                signal_id=context_signal_id,
                workspace_id=resolved_workspace_id,
            )
        ]
        reply = _short_reply_summary(runtime_reply)
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

    if reply:
        reply = normalize_spoken_line(reply)

    _note_briefing_surface_offer(session_id, reply)
    _remember_turn(session_id, "user", trimmed)
    _remember_turn(session_id, "assistant", reply)

    return _log_voice_turn(
        session_id=session_id,
        workspace_id=workspace_id,
        raw_content=raw_content,
        normalized_content=trimmed,
        payload={
            "turn_kind": turn_kind,
            "reply": reply,
            "source": source,
            "command_content": command_content,
            "requires_confirmation": requires_confirmation if turn_kind == "command" else None,
            "action": None,
            "artifacts": artifacts,
        },
        duration_ms=round((time.perf_counter() - started_at) * 1000),
        runtime_dispatched=runtime_dispatched,
    )


__all__ = [
    "answer_status_question",
    "build_conversation_context_pack",
    "classify_conversation_turn",
    "converse_turn",
]
