"""Independent VAXON voice-turn routing (lanes + model pool receipts).

Default voice turns must not silently inherit IDE Composer preferences.
Task-based lanes choose template/status, bounded command, VAXON runtime, or
explicit IDE handoff; every runtime selection records a failover receipt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal

from app.chat.command_intent import (
    classify_command,
    command_requires_confirmation,
    expand_command_shortcuts,
)
from app.cli_runtime.catalog import runtime_status_snapshot
from app.cli_runtime.recovery import ordered_runtime_candidates
from app.kairo.teammate_handoff import build_specialty_task_action
from app.kairo.voice_autonomy import resolve_voice_action_tier
from app.kairo_conversation_reply import (
    compose_conversation_reply,
    compose_smalltalk_reply,
)
from app.kairo_conversation_runtime_context import OPEN_DETAIL_RE, STATUS_REPORT_RE
from app.kairo_voice import normalize_spoken_line

VoiceDispatchLane = Literal[
    "template_status",
    "bounded_command",
    "vaxon_runtime",
    "ide_handoff",
    "deterministic_report",
]
VoiceRoutingMode = Literal["template_first", "runtime_on_deep", "runtime_aggressive"]
ConversationAnswerTier = Literal["fast", "deep"]
ConversationSource = Literal["template", "model", "fallback"]
ConversationTurnKind = Literal["status_question", "open_question", "command", "chat", "action"]

_MAX_RUNTIME_VOICE_REPLY_CHARS = 1200

# Dedicated VAXON pool — independent from IDE Composer UI selection.
_DEFAULT_VAXON_MODEL_POOL = (
    "composer-2",
    "gpt-5.4-high",
    "claude-sonnet-5-thinking-high",
)


def _short_spoken_summary(
    reply: str,
    *,
    max_chars: int = 280,
    max_sentences: int = 2,
) -> str:
    import re

    trimmed = re.sub(r"\s+", " ", reply.strip())
    if not trimmed:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", trimmed)
    summary = ""
    sentence_count = 0
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        next_summary = f"{summary} {candidate}".strip()
        if len(next_summary) > max_chars:
            break
        summary = next_summary
        sentence_count += 1
        if sentence_count >= max_sentences:
            break
    if summary:
        return summary
    if len(trimmed) <= max_chars:
        return trimmed
    shortened = trimmed[: max_chars - 1].rstrip(" ,;:")
    return f"{shortened}…"


def _spoken_delivery_summary(reply: str, *, deep: bool) -> str:
    """TTS may be shorter than the UI reply; deep/status reports keep more detail."""
    if deep:
        return _short_spoken_summary(reply, max_chars=900, max_sentences=6)
    return _short_spoken_summary(reply, max_chars=280, max_sentences=2)


@dataclass(frozen=True)
class VoiceModelReceipt:
    selected_model: str | None
    runtime_id: str | None
    runtime_label: str | None
    lane: VoiceDispatchLane
    reason: str
    duration_ms: int | None = None
    fallback: bool = False
    attempts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_model": self.selected_model,
            "runtime_id": self.runtime_id,
            "runtime_label": self.runtime_label,
            "lane": self.lane,
            "reason": self.reason,
            "duration_ms": self.duration_ms,
            "fallback": self.fallback,
            "attempts": list(self.attempts),
        }

    def as_line(self) -> str:
        model = self.selected_model or "none"
        runtime = self.runtime_id or "none"
        return (
            f"lane={self.lane} model={model} runtime={runtime} "
            f"reason={self.reason} fallback={str(self.fallback).lower()}"
        )


@dataclass
class VoiceDispatchDecision:
    lane: VoiceDispatchLane
    turn_kind: ConversationTurnKind
    source: ConversationSource
    reply: str
    spoken_reply: str | None = None
    command_content: str | None = None
    requires_confirmation: bool | None = None
    action_tier: str | None = None
    action: dict[str, object] | None = None
    artifacts: list[dict[str, object]] = field(default_factory=list)
    runtime_dispatched: bool = False
    model_receipt: VoiceModelReceipt | None = None


def normalize_voice_routing_mode(raw: object) -> VoiceRoutingMode:
    value = str(raw or "").strip().lower()
    if value in {"template_first", "runtime_on_deep", "runtime_aggressive"}:
        return value  # type: ignore[return-value]
    return "template_first"


def vaxon_model_pool() -> list[str]:
    configured = str(os.environ.get("AXON_VAXON_MODEL_POOL") or "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    return list(_DEFAULT_VAXON_MODEL_POOL)


def select_vaxon_runtime(
    *,
    preferred_model: str | None = None,
) -> tuple[str | None, str | None, str | None, list[str]]:
    """Pick a ready runtime from the VAXON pool; return id, label, model, attempt trail."""
    snapshot = runtime_status_snapshot()
    candidates = ordered_runtime_candidates(snapshot)
    pool = vaxon_model_pool()
    attempts: list[str] = []
    preferred = (preferred_model or "").strip() or None

    def matches_pool(record: dict[str, Any]) -> bool:
        model = str(record.get("model") or record.get("default_model") or "").strip()
        runtime_id = str(record.get("id") or "").strip()
        label = str(record.get("label") or "").strip()
        haystack = f"{model} {runtime_id} {label}".lower()
        if preferred and preferred.lower() in haystack:
            return True
        return any(token.lower() in haystack for token in pool)

    ordered = [record for record in candidates if matches_pool(record)]
    if not ordered:
        ordered = list(candidates)

    for record in ordered:
        runtime_id = str(record.get("id") or "").strip() or None
        label = str(record.get("label") or runtime_id or "").strip() or None
        model = str(record.get("model") or record.get("default_model") or "").strip() or None
        ready = bool(record.get("ready"))
        attempts.append(f"{runtime_id or 'unknown'}:{'ready' if ready else 'skip'}")
        if not ready or not runtime_id:
            continue
        return runtime_id, label, model, attempts

    return None, None, None, attempts


def should_use_vaxon_runtime(
    *,
    turn_kind: ConversationTurnKind,
    content: str,
    use_runtime: bool,
    answer_tier: ConversationAnswerTier,
    voice_routing_mode: VoiceRoutingMode,
) -> bool:
    mode = normalize_voice_routing_mode(voice_routing_mode)
    if turn_kind not in {"open_question", "status_question"}:
        return False
    if mode == "runtime_aggressive":
        if turn_kind == "open_question":
            return True
        return bool(OPEN_DETAIL_RE.search(content))
    if mode == "runtime_on_deep":
        if not use_runtime and answer_tier != "deep":
            return False
        if answer_tier == "deep":
            return True
        return bool(use_runtime and OPEN_DETAIL_RE.search(content))
    # template_first: keep app voice local, but honor explicit runtime requests
    # (omnibar deep / use_runtime=True) so IDE Composer is not the default path.
    if not use_runtime:
        return False
    if answer_tier == "deep":
        return True
    return bool(OPEN_DETAIL_RE.search(content))


def route_voice_turn(
    *,
    content: str,
    session_id: str,
    workspace_id: str | None,
    pack: dict[str, Any],
    turn_kind: ConversationTurnKind,
    voice_routing_mode: str,
    use_runtime: bool,
    answer_tier: ConversationAnswerTier,
    recent_turns: list[dict[str, str]],
    command_ack_line,
    workspace_short_label,
    build_runtime_artifact,
    build_runtime_context_block,
    remember_entities,
    remember_top_signal,
    dispatch_runtime,
    context_signal_id: str | None = None,
    context_node_id: str | None = None,
    preferred_model: str | None = None,
) -> VoiceDispatchDecision:
    """Route a classified turn into a VAXON lane with autonomy + model receipts."""
    mode = normalize_voice_routing_mode(voice_routing_mode)

    from app.kairo.operator_deterministic_report import (
        build_operator_report_snapshot,
        compose_operator_report,
        is_operator_report_request,
    )

    # Dedicated REPORT lane — never Lane B / runtime; roster + verified handoffs only.
    if is_operator_report_request(content):
        snapshot = build_operator_report_snapshot(
            workspace_id=workspace_id,
            pack=pack,
            force_refresh=True,
        )
        composed = compose_operator_report(snapshot)
        reply = str(composed.get("text") or "").strip()
        spoken = str(composed.get("spoken") or reply).strip()
        receipt = VoiceModelReceipt(
            selected_model=None,
            runtime_id=None,
            runtime_label=None,
            lane="deterministic_report",
            reason=f"fingerprint={composed.get('fingerprint') or 'none'}",
            fallback=False,
        )
        remember_top_signal(session_id, pack, fallback_workspace_id=workspace_id)
        return VoiceDispatchDecision(
            lane="deterministic_report",
            turn_kind="status_question",
            source="template",
            reply=reply,
            spoken_reply=spoken or reply,
            model_receipt=receipt,
        )

    if turn_kind == "command":
        normalized = expand_command_shortcuts(content)
        requires_confirmation = command_requires_confirmation(normalized)
        tier = resolve_voice_action_tier(normalized)
        if tier.requires_approval:
            requires_confirmation = True
        reply = command_ack_line(normalized, workspace_label=workspace_short_label(pack))
        if requires_confirmation:
            remember_entities(session_id, pending_command=normalized)
        else:
            # Auto-dispatch commands must not leave a stale confirm target.
            remember_entities(session_id, pending_command="")
        receipt = VoiceModelReceipt(
            selected_model=None,
            runtime_id=None,
            runtime_label=None,
            lane="bounded_command",
            reason=f"intent={classify_command(normalized)};tier={tier.tier}",
            fallback=False,
        )
        return VoiceDispatchDecision(
            lane="bounded_command",
            turn_kind="command",
            source="template",
            reply=reply,
            command_content=normalized,
            requires_confirmation=requires_confirmation,
            action_tier=tier.tier,
            model_receipt=receipt,
        )

    if turn_kind in {"chat", "open_question"}:
        specialty_action = build_specialty_task_action(
            content,
            workspace_id=workspace_id,
        )
        if specialty_action is not None:
            employee_name = str(specialty_action.get("employee_name") or "the specialist")
            employee_role = str(specialty_action.get("employee_role") or "specialist")
            return VoiceDispatchDecision(
                lane="ide_handoff",
                turn_kind="action",
                source="model" if specialty_action.get("model_receipt") else "template",
                reply=f"Routing this to {employee_name}, your {employee_role} specialist.",
                action_tier="reversible_auto",
                action=specialty_action,
            )

    if turn_kind == "status_question" and not should_use_vaxon_runtime(
        turn_kind=turn_kind,
        content=content,
        use_runtime=use_runtime,
        answer_tier=answer_tier,
        voice_routing_mode=mode,
    ):
        reply = compose_conversation_reply(
            content=content,
            pack=pack,
            session_id=session_id,
            recent_turns=recent_turns,
        )
        remember_top_signal(session_id, pack, fallback_workspace_id=workspace_id)
        receipt = VoiceModelReceipt(
            selected_model=None,
            runtime_id=None,
            runtime_label=None,
            lane="template_status",
            reason=f"routing={mode}",
        )
        return VoiceDispatchDecision(
            lane="template_status",
            turn_kind="status_question",
            source="template",
            reply=reply,
            model_receipt=receipt,
        )

    if should_use_vaxon_runtime(
        turn_kind=turn_kind if turn_kind in {"open_question", "status_question"} else "open_question",
        content=content,
        use_runtime=use_runtime,
        answer_tier=answer_tier,
        voice_routing_mode=mode,
    ):
        runtime_id, runtime_label, model, attempts = select_vaxon_runtime(
            preferred_model=preferred_model,
        )
        context_block = build_runtime_context_block(
            content=content,
            workspace_id=str(workspace_id or ""),
            pack=pack,
            session_id=session_id,
            recent_turns=recent_turns,
            context_node_id=context_node_id,
            context_signal_id=context_signal_id,
        )
        payload = dispatch_runtime(
            workspace_id=str(workspace_id or ""),
            composer_mode="ask",
            user_prompt=content,
            context_block=context_block,
            execution_access="consultative",
            runtime_target=runtime_id,
            runtime_model=model,
        )
        reply = normalize_spoken_line(
            str(payload.get("content") or ""),
            max_chars=_MAX_RUNTIME_VOICE_REPLY_CHARS,
        )
        dispatched = bool(payload.get("dispatched")) and bool(reply)
        if not reply:
            reply = compose_conversation_reply(
                content=content,
                pack=pack,
                session_id=session_id,
                recent_turns=recent_turns,
            )
            source: ConversationSource = "fallback"
        else:
            source = "model" if dispatched else "fallback"
        fallback = source != "model"
        selected_runtime = str(payload.get("runtime_id") or runtime_id or "") or None
        selected_label = str(payload.get("runtime_label") or runtime_label or "") or None
        selected_model = str(payload.get("runtime_model") or model or "") or None
        reason = str(payload.get("reason") or ("dispatched" if dispatched else "runtime_unavailable"))
        failure_phase = str(payload.get("failure_phase") or "").strip()
        if failure_phase and failure_phase not in reason:
            reason = f"{failure_phase};{reason}"
        receipt = VoiceModelReceipt(
            selected_model=selected_model,
            runtime_id=selected_runtime,
            runtime_label=selected_label,
            lane="vaxon_runtime",
            reason=reason,
            fallback=fallback,
            attempts=tuple(attempts),
        )
        artifacts = [
            build_runtime_artifact(
                content=content,
                reply=reply,
                pack=pack,
                signal_id=context_signal_id,
                workspace_id=workspace_id,
            )
        ]
        # UI/transcript keep the full reply; TTS may use a shorter spoken_reply.
        deep = (
            answer_tier == "deep"
            or bool(OPEN_DETAIL_RE.search(content))
            or bool(STATUS_REPORT_RE.search(content))
        )
        spoken = _spoken_delivery_summary(reply, deep=deep)
        remember_top_signal(session_id, pack, fallback_workspace_id=workspace_id)
        return VoiceDispatchDecision(
            lane="vaxon_runtime",
            turn_kind=turn_kind,
            source=source,
            reply=reply,
            spoken_reply=spoken or reply,
            artifacts=artifacts,
            runtime_dispatched=source == "model",
            model_receipt=receipt,
        )

    smalltalk = compose_smalltalk_reply(
        content=content,
        session_id=session_id,
        recent_turns=recent_turns,
    )
    if smalltalk:
        reply = smalltalk
    else:
        reply = compose_conversation_reply(
            content=content,
            pack=pack,
            session_id=session_id,
            recent_turns=recent_turns,
        )
    receipt = VoiceModelReceipt(
        selected_model=None,
        runtime_id=None,
        runtime_label=None,
        lane="template_status",
        reason=f"routing={mode};turn={turn_kind}",
    )
    return VoiceDispatchDecision(
        lane="template_status",
        turn_kind=turn_kind,
        source="template",
        reply=reply,
        model_receipt=receipt,
    )
