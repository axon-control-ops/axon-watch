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
from app.cli_runtime.router import dispatch_ide_composer
from app.kairo.context_pack_cache import get_cached_context_pack
from app.kairo.voice_dispatch import VoiceModelReceipt, normalize_voice_routing_mode, route_voice_turn
from app.kairo.voice_autonomy import resolve_voice_action_tier
from app.kairo_memory_intents import maybe_handle_memory_intent
from app.persistence.operator_presence_settings_store import load_settings as load_presence_settings
from app.kairo.turn_memory import (
    entity_context as _entity_context,
    note_briefing_surface_offer as _note_briefing_surface_offer,
    recent_turns as _recent_turns,
    remember_entities as _remember_entities,
    remember_top_signal as _remember_top_signal,
    remember_turn as _remember_turn,
    resolve_followup_action as _resolve_followup_action,
)
from app.kairo.mission_memory import (
    maybe_capture_explicit_remember,
    propose_mission_action,
    resolve_mission_confirmation,
)

from app.kairo.conversation_artifacts import (
    build_runtime_artifact,
    should_use_runtime_for_open_question,
)
from app.kairo.conversation_command_ack import command_ack_line, workspace_short_label
from app.kairo.conversation_context_pack import build_conversation_context_pack
from app.kairo.teammate_handoff import enrich_handoff_with_teammate
from app.kairo.conversation_transcript import log_voice_turn as _log_voice_turn
from app.kairo_conversation_reply import (
    build_conversation_facts,
    compose_conversation_reply,
    compose_smalltalk_reply,
    is_open_style_question,
)
from app.kairo_conversation_runtime_context import (
    OPEN_DETAIL_RE as _OPEN_DETAIL_RE,
    build_runtime_context_block,
    runtime_workspace_id,
)
from app.kairo_participant_memory import (
    apply_participant_address,
    get_active_participant,
    update_participant_from_utterance,
)
from app.kairo_workspace_intents import infer_workspace_id_from_content
from app.kairo_voice import normalize_spoken_line
from app.operator_briefing import build_operator_briefing
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_fleet_health import build_operator_fleet_health
from app.operator_persona_stt_aliases import normalize_persona_stt_aliases
from app.persistence import chat_store
from app.workspace_project_bindings import get_workspace_project_binding, load_workspace_project_bindings
ConversationTurnKind = Literal["status_question", "open_question", "command", "chat", "action"]
ConversationSource = Literal["template", "model", "fallback"]; ConversationAnswerTier = Literal["fast", "deep"]
_MAX_RUNTIME_VOICE_REPLY_CHARS = 1200

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
def _runtime_workspace_id(*, workspace_id: str | None, pack: dict[str, Any]) -> str:
    return runtime_workspace_id(workspace_id=workspace_id, pack=pack)


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
    return build_runtime_context_block(
        content=content,
        workspace_id=workspace_id,
        pack=pack,
        session_id=session_id,
        recent_turns=recent_turns,
        context_node_id=context_node_id,
        context_signal_id=context_signal_id,
    )


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
    force_refresh: bool = False,
) -> dict[str, object]:
    started_at = time.perf_counter()
    raw_content = content.strip()
    trimmed = normalize_persona_stt_aliases(raw_content)
    if not trimmed:
        raise ValueError("content must not be empty")

    guest_name = update_participant_from_utterance(session_id, trimmed)

    tier: ConversationAnswerTier = "deep" if str(answer_tier).strip().lower() == "deep" else "fast"
    inferred_workspace_id = infer_workspace_id_from_content(trimmed)
    entity = _entity_context(session_id)
    entity_workspace_id = entity.get("target_workspace_id") or None
    resolved_workspace_id = (
        context_workspace_id or workspace_id or inferred_workspace_id or entity_workspace_id
    )
    pack = build_conversation_context_pack(
        workspace_id=resolved_workspace_id,
        force_refresh=force_refresh,
    )
    presence_settings = load_presence_settings()
    voice_routing_mode = normalize_voice_routing_mode(
        presence_settings.get("voice_routing_mode")
    )
    if context_signal_id and resolved_workspace_id:
        _remember_entities(
            session_id,
            signal_id=context_signal_id,
            target_workspace_id=resolved_workspace_id,
            task=f"Investigate signal {context_signal_id}",
        )
    maybe_capture_explicit_remember(session_id, trimmed)
    mission_confirm = resolve_mission_confirmation(session_id, trimmed)
    if mission_confirm:
        reply = apply_participant_address(str(mission_confirm.get("reply") or ""), guest_name)
        _remember_turn(session_id, "user", trimmed)
        _remember_turn(session_id, "assistant", reply)
        return _log_voice_turn(
            session_id=session_id,
            workspace_id=workspace_id,
            raw_content=raw_content,
            normalized_content=trimmed,
            payload={
                "turn_kind": "action" if mission_confirm.get("action") else "chat",
                "reply": reply,
                "source": "template",
                "command_content": None,
                "requires_confirmation": False,
                "action": mission_confirm.get("action"),
                "artifacts": [],
                "active_participant": guest_name,
            },
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )
    mission_propose = propose_mission_action(
        session_id,
        trimmed,
        workspace_id=str(resolved_workspace_id or ""),
    )
    if mission_propose:
        reply = apply_participant_address(str(mission_propose.get("reply") or ""), guest_name)
        _remember_turn(session_id, "user", trimmed)
        _remember_turn(session_id, "assistant", reply)
        return _log_voice_turn(
            session_id=session_id,
            workspace_id=workspace_id,
            raw_content=raw_content,
            normalized_content=trimmed,
            payload={
                "turn_kind": "chat",
                "reply": reply,
                "source": "template",
                "command_content": None,
                "requires_confirmation": True,
                "action": None,
                "artifacts": [],
                "active_participant": guest_name,
            },
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )
    followup = _resolve_followup_action(trimmed, session_id)
    if followup:
        action_type = str(followup.get("type", ""))
        if action_type == "handoff_signal":
            followup = enrich_handoff_with_teammate(
                followup,
                resolved_workspace_id=resolved_workspace_id,
                fallback_prompt=trimmed,
            )
            reply = apply_participant_address(
                "Handing this off to the IDE now.",
                guest_name,
            )
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
                    "active_participant": guest_name,
                },
                duration_ms=round((time.perf_counter() - started_at) * 1000),
            )
        if action_type == "dispatch_command":
            command_content = str(followup.get("content", "")).strip()
            reply = apply_participant_address(
                command_ack_line(
                    command_content,
                    workspace_label=workspace_short_label(pack),
                ),
                guest_name,
            )
            tier = resolve_voice_action_tier(command_content)
            receipt = VoiceModelReceipt(
                selected_model=None,
                runtime_id=None,
                runtime_label=None,
                lane="bounded_command",
                reason=f"followup_confirm;intent={tier.intent};tier={tier.tier}",
                fallback=False,
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
                    "requires_confirmation": False,
                    "action_tier": tier.tier,
                    "dispatch_lane": "bounded_command",
                    "voice_routing_mode": voice_routing_mode,
                    "model_receipt": receipt.as_dict(),
                    "routing_receipt": receipt.as_line(),
                    "action": followup,
                    "artifacts": [],
                    "active_participant": guest_name,
                },
                duration_ms=round((time.perf_counter() - started_at) * 1000),
            )
        if action_type == "focus_briefing":
            reply = apply_participant_address(
                "Opening the briefing for you.",
                guest_name,
            )
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
                    "active_participant": guest_name,
                },
                duration_ms=round((time.perf_counter() - started_at) * 1000),
            )

    memory_intent = maybe_handle_memory_intent(
        content=trimmed,
        session_id=session_id,
        workspace_id=resolved_workspace_id,
        guest_name=guest_name,
    )
    if memory_intent is not None:
        reply = str(memory_intent.get("reply") or "")
        _remember_turn(session_id, "user", trimmed)
        _remember_turn(session_id, "assistant", reply)
        return _log_voice_turn(
            session_id=session_id,
            workspace_id=workspace_id,
            raw_content=raw_content,
            normalized_content=trimmed,
            payload={
                "turn_kind": str(memory_intent.get("turn_kind") or "action"),
                "reply": reply,
                "source": str(memory_intent.get("source") or "template"),
                "command_content": memory_intent.get("command_content"),
                "action": memory_intent.get("action"),
                "artifacts": list(memory_intent.get("artifacts") or []),
                "active_participant": guest_name,
            },
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )

    from app.chat.move_voice_orb import move_voice_orb_ack, parse_move_voice_orb_ui_action

    move_orb_action = parse_move_voice_orb_ui_action(trimmed)
    if move_orb_action is not None:
        reply = apply_participant_address(
            move_voice_orb_ack(move_orb_action),
            guest_name or get_active_participant(session_id),
        )
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
                "action": move_orb_action,
                "artifacts": [],
                "active_participant": guest_name or get_active_participant(session_id),
                "action_tier": "reversible_auto",
            },
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )

    turn_kind = classify_conversation_turn(trimmed)
    # Keep caller use_runtime; voice_routing_mode gates lanes inside the router.
    recent = _recent_turns(session_id)
    decision = route_voice_turn(
        content=trimmed,
        session_id=session_id,
        workspace_id=resolved_workspace_id,
        pack=pack,
        turn_kind=turn_kind,
        voice_routing_mode=voice_routing_mode,
        use_runtime=use_runtime,
        answer_tier=tier,
        recent_turns=recent,
        command_ack_line=command_ack_line,
        workspace_short_label=workspace_short_label,
        build_runtime_artifact=build_runtime_artifact,
        build_runtime_context_block=_build_runtime_context_block,
        remember_entities=_remember_entities,
        remember_top_signal=_remember_top_signal,
        dispatch_runtime=dispatch_ide_composer,
        context_signal_id=context_signal_id,
        context_node_id=context_node_id,
    )

    reply = decision.reply
    source = decision.source
    command_content = decision.command_content
    artifacts = decision.artifacts
    runtime_dispatched = decision.runtime_dispatched
    requires_confirmation = decision.requires_confirmation
    model_receipt = decision.model_receipt.as_dict() if decision.model_receipt else None

    if reply:
        reply = normalize_spoken_line(reply)
        reply = apply_participant_address(reply, guest_name or get_active_participant(session_id))

    _note_briefing_surface_offer(session_id, reply)
    _remember_turn(session_id, "user", trimmed)
    _remember_turn(session_id, "assistant", reply)

    return _log_voice_turn(
        session_id=session_id,
        workspace_id=workspace_id,
        raw_content=raw_content,
        normalized_content=trimmed,
        payload={
            "turn_kind": decision.turn_kind,
            "reply": reply,
            "source": source,
            "command_content": command_content,
            "requires_confirmation": requires_confirmation if decision.turn_kind == "command" else None,
            "action_tier": decision.action_tier,
            "dispatch_lane": decision.lane,
            "voice_routing_mode": voice_routing_mode,
            "model_receipt": model_receipt,
            "routing_receipt": decision.model_receipt.as_line() if decision.model_receipt else None,
            "action": decision.action,
            "artifacts": artifacts,
            "active_participant": guest_name or get_active_participant(session_id),
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