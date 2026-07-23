"""Mission-memory early returns for KAIRO converse turns."""

from __future__ import annotations

import time

from app.kairo.conversation_transcript import log_voice_turn as _log_voice_turn
from app.kairo.mission_memory import (
    maybe_capture_explicit_remember,
    propose_mission_action,
    resolve_mission_confirmation,
)
from app.kairo.turn_memory import remember_turn as _remember_turn
from app.kairo_participant_memory import apply_participant_address


def try_mission_memory_turn(
    *,
    session_id: str,
    trimmed: str,
    raw_content: str,
    workspace_id: str,
    resolved_workspace_id: str | None,
    guest_name: str,
    started_at: float,
) -> dict[str, object] | None:
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
    if not mission_propose:
        return None
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
