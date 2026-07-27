"""Early VAXON converse intents that must not fall through to fleet templates."""

from __future__ import annotations

from typing import Any

from app.chat.move_voice_orb import move_voice_orb_ack, parse_move_voice_orb_ui_action
from app.kairo_memory_intents import maybe_handle_memory_intent
from app.kairo_participant_memory import apply_participant_address, get_active_participant
from app.kairo_workspace_register_intents import maybe_handle_register_workspace_intent
from app.kairo_workspace_rename_intents import maybe_handle_rename_workspace_intent


def maybe_handle_early_converse_intent(
    *,
    content: str,
    session_id: str,
    workspace_id: str | None,
    guest_name: str | None,
) -> dict[str, Any] | None:
    memory_intent = maybe_handle_memory_intent(
        content=content,
        session_id=session_id,
        workspace_id=workspace_id,
        guest_name=guest_name,
    )
    if memory_intent is not None:
        return memory_intent

    move_orb_action = parse_move_voice_orb_ui_action(content)
    if move_orb_action is not None:
        participant = guest_name or get_active_participant(session_id)
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(move_voice_orb_ack(move_orb_action), participant),
            "source": "template",
            "command_content": None,
            "action": move_orb_action,
            "artifacts": [],
            "active_participant": participant,
            "action_tier": "reversible_auto",
        }

    rename_intent = maybe_handle_rename_workspace_intent(
        content=content,
        workspace_id=workspace_id,
        guest_name=guest_name,
    )
    if rename_intent is not None:
        return rename_intent

    return maybe_handle_register_workspace_intent(content=content, guest_name=guest_name)
