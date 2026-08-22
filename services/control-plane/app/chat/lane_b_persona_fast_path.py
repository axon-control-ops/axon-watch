"""Fast paths for persona-style IDE agent prompts that should not spawn Lane B."""

from __future__ import annotations

import re
from typing import Any, Callable

from app.kairo_conversation_reply import compose_smalltalk_reply
from app.operator_persona_stt_aliases import normalize_persona_stt_aliases


def build_ambiguous_reply_guard(content: str) -> str | None:
    """Fail closed for a bare option number sent through the free-text composer.

    Option selections are only authoritative when the UI submits the option-card
    event with its question id.  Treating a free-text ``"2"`` as a selection can
    bind it to an old question and cause an invented handoff.
    """
    if re.fullmatch(r"[1-9]", str(content or "").strip()) is None:
        return None
    return (
        "I did not treat that number as a task decision because this composer "
        "message is not tied to a specific decision card. Please select the option "
        "on its card, or send the full action in words. No task, handoff, command, "
        "or file change was created."
    )


def build_lane_b_persona_reply(
    *,
    content: str,
    recent_turns: list[dict[str, str]],
    session_id: str,
) -> str | None:
    trimmed = normalize_persona_stt_aliases(content).strip()
    if not trimmed:
        return None
    return compose_smalltalk_reply(
        content=trimmed,
        session_id=session_id,
        recent_turns=recent_turns,
    )


def post_lane_b_persona_message(
    *,
    workspace_id: str,
    content: str,
    thread_id: str,
    created_at: str,
    save_message: Callable[[dict[str, Any]], dict[str, Any]],
    new_message_id: Callable[[str], str],
    bind_attachments: Callable[[str], list[dict[str, object]]],
    agent_content: str,
) -> dict[str, object]:
    operator_message = save_message(
        {
            "message_id": new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "operator",
            "content": content,
            "created_at": created_at,
        }
    )
    operator_attachments = bind_attachments(str(operator_message["message_id"]))
    if operator_attachments:
        operator_message = {**operator_message, "attachments": operator_attachments}
    system_message = save_message(
        {
            "message_id": new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "system",
            "content": "VAXON local reply in IDE; no Lane B dispatch.",
            "created_at": created_at,
        }
    )
    agent_message = save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )
    return {
        "thread_id": thread_id,
        "messages": [operator_message, system_message, agent_message],
        "run_id": "",
        "dispatched": False,
        "run": None,
        "streaming": False,
    }
