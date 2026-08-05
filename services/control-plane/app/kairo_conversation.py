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
from app.kairo.voice_dispatch import (
    VoiceModelReceipt,
    normalize_voice_routing_mode,
    resolve_vaxon_model,
    route_voice_turn,
)
from app.kairo.voice_autonomy import resolve_voice_action_tier
from app.kairo_early_intents import maybe_handle_early_converse_intent
from app.persistence.operator_presence_settings_store import load_settings as load_presence_settings
from app.kairo.turn_memory import (
    entity_context as _entity_context,
    note_briefing_surface_offer as _note_briefing_surface_offer,
    note_followup_offers as _note_followup_offers,
    recent_turns as _recent_turns,
    remember_entities as _remember_entities,
    remember_top_signal as _remember_top_signal,
    remember_turn as _remember_turn,
    resolve_followup_action as _resolve_followup_action,
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
    image_paths: tuple[str, ...] = (),
) -> str:
    return build_runtime_context_block(
        content=content,
        workspace_id=workspace_id,
        pack=pack,
        session_id=session_id,
        recent_turns=recent_turns,
        context_node_id=context_node_id,
        context_signal_id=context_signal_id,
        image_paths=image_paths,
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
    attachment_ids: list[str] | None = None,
    submission_intent: str = "ask",
) -> dict[str, object]:
    started_at = time.perf_counter()
    raw_content = content.strip()
    trimmed = normalize_persona_stt_aliases(raw_content)
    if not trimmed:
        raise ValueError("content must not be empty")
    from app.kairo.operator_input_safety import is_pasted_operational_context

    pasted_operational_context = is_pasted_operational_context(trimmed)
    dispatch_requested = str(submission_intent or "").strip().lower() == "dispatch"
    allow_actions = dispatch_requested and not pasted_operational_context

    def _record_turn(**kwargs: object) -> dict[str, object]:
        payload = dict(kwargs.get("payload") or {})
        payload["submission_intent"] = "dispatch" if dispatch_requested else "ask"
        kwargs["payload"] = payload
        return _log_voice_turn(**kwargs)  # type: ignore[arg-type]

    from app.kairo.converse_attachments import ConverseAttachmentError, prepare_converse_attachment_paths

    if attachment_ids:
        use_runtime = True
        answer_tier = "deep"
    guest_name = update_participant_from_utterance(session_id, trimmed)
    tier: ConversationAnswerTier = "deep" if str(answer_tier).strip().lower() == "deep" else "fast"
    inferred_workspace_id = infer_workspace_id_from_content(trimmed)
    entity = _entity_context(session_id)
    resolved_workspace_id = (
        context_workspace_id
        or workspace_id
        or inferred_workspace_id
        or entity.get("target_workspace_id")
        or None
    )
    try:
        image_paths = prepare_converse_attachment_paths(
            attachment_ids=attachment_ids,
            workspace_id=str(resolved_workspace_id or workspace_id or ""),
        )
    except ConverseAttachmentError as exc:
        raise ValueError(str(exc)) from exc
    from app.kairo.operator_deterministic_report import is_operator_report_request

    # REPORT always needs a fresh briefing/roster snapshot — ignore cache TTL.
    pack = build_conversation_context_pack(
        workspace_id=resolved_workspace_id,
        force_refresh=force_refresh or is_operator_report_request(trimmed),
    )
    presence_settings = load_presence_settings()
    voice_routing_mode = normalize_voice_routing_mode(
        presence_settings.get("voice_routing_mode")
    )
    preferred_vaxon_model = resolve_vaxon_model(presence_settings.get("vaxon_model_id"))
    if context_signal_id and resolved_workspace_id:
        _remember_entities(
            session_id,
            signal_id=context_signal_id,
            target_workspace_id=resolved_workspace_id,
            task=f"Investigate signal {context_signal_id}",
        )
    # Ask turns and quoted receipts must not confirm a remembered action or
    # trigger one of the convenience action routes below.
    followup = _resolve_followup_action(trimmed, session_id) if allow_actions else None
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
            _remember_entities(session_id, pending_dig_in="")
            _remember_turn(session_id, "user", trimmed)
            _remember_turn(session_id, "assistant", reply)
            return _record_turn(
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
            return _record_turn(
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
            return _record_turn(
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

    early_intent = (
        maybe_handle_early_converse_intent(
            content=trimmed,
            session_id=session_id,
            workspace_id=resolved_workspace_id,
            guest_name=guest_name,
        )
        if allow_actions
        else None
    )
    if early_intent is not None:
        reply = str(early_intent.get("reply") or "")
        participant = early_intent.get("active_participant") or guest_name
        _remember_turn(session_id, "user", trimmed)
        _remember_turn(session_id, "assistant", reply)
        payload = {
            "turn_kind": str(early_intent.get("turn_kind") or "action"),
            "reply": reply,
            "source": str(early_intent.get("source") or "template"),
            "command_content": early_intent.get("command_content"),
            "action": early_intent.get("action"),
            "artifacts": list(early_intent.get("artifacts") or []),
            "active_participant": participant,
        }
        if early_intent.get("action_tier"):
            payload["action_tier"] = early_intent.get("action_tier")
        return _record_turn(
            session_id=session_id,
            workspace_id=workspace_id,
            raw_content=raw_content,
            normalized_content=trimmed,
            payload=payload,
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )

    turn_kind = classify_conversation_turn(trimmed)
    # Ask is an answer-only capability. Command-looking text is still useful
    # evidence, but it must not reach the bounded-command lane without Dispatch.
    if not dispatch_requested and turn_kind == "command":
        turn_kind = "status_question"
    # Ask is VAXON's consultative COO lane — force deep quality without vocabulary traps.
    if not dispatch_requested:
        tier = "deep"
    # Keep caller use_runtime; voice_routing_mode gates lanes inside the router.
    recent = _recent_turns(session_id)
    consultative_workspace_id = _runtime_workspace_id(
        workspace_id=resolved_workspace_id,
        pack=pack,
    )

    def _runtime_context_with_attachments(**kwargs: Any) -> str:
        return _build_runtime_context_block(**kwargs, image_paths=image_paths)

    decision = route_voice_turn(
        content=trimmed,
        session_id=session_id,
        workspace_id=consultative_workspace_id,
        pack=pack,
        turn_kind=turn_kind,
        voice_routing_mode=voice_routing_mode,
        use_runtime=use_runtime or bool(image_paths),
        answer_tier=tier,
        recent_turns=recent,
        command_ack_line=command_ack_line,
        workspace_short_label=workspace_short_label,
        build_runtime_artifact=build_runtime_artifact,
        build_runtime_context_block=_runtime_context_with_attachments,
        remember_entities=_remember_entities,
        remember_top_signal=_remember_top_signal,
        dispatch_runtime=dispatch_ide_composer,
        context_signal_id=context_signal_id,
        context_node_id=context_node_id,
        preferred_model=preferred_vaxon_model,
        allow_actions=allow_actions,
        consultative=not dispatch_requested,
    )

    reply = decision.reply
    spoken_reply = decision.spoken_reply
    source = decision.source
    command_content = decision.command_content
    artifacts = decision.artifacts
    runtime_dispatched = decision.runtime_dispatched
    requires_confirmation = decision.requires_confirmation
    model_receipt = decision.model_receipt.as_dict() if decision.model_receipt else None
    listener = guest_name or get_active_participant(session_id)

    if reply:
        reply = apply_participant_address(normalize_spoken_line(reply), listener)
    if spoken_reply:
        spoken_reply = apply_participant_address(normalize_spoken_line(spoken_reply), listener)

    _note_followup_offers(session_id, reply)
    _remember_turn(session_id, "user", trimmed)
    _remember_turn(session_id, "assistant", reply)

    return _record_turn(
        session_id=session_id,
        workspace_id=workspace_id,
        raw_content=raw_content,
        normalized_content=trimmed,
        payload={
            "turn_kind": decision.turn_kind,
            "reply": reply,
            "spoken_reply": spoken_reply,
            "source": source,
            "command_content": command_content,
            "requires_confirmation": requires_confirmation if decision.turn_kind == "command" else None,
            "action_tier": decision.action_tier,
            "dispatch_lane": decision.lane,
            "voice_routing_mode": voice_routing_mode,
            "vaxon_model_id": preferred_vaxon_model,
            "model_receipt": model_receipt,
            "routing_receipt": decision.model_receipt.as_line() if decision.model_receipt else None,
            "action": decision.action,
            "artifacts": artifacts,
            "active_participant": listener,
            "report": decision.report,
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