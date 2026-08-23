"""Persist completed Lane B turns in Kairo conversation memory."""

from __future__ import annotations

from app.kairo.turn_memory import remember_turn


def remember_lane_b_turn(
    *,
    kairo_session_id: str | None,
    operator_content: str,
    agent_content: str,
) -> None:
    session = str(kairo_session_id or "").strip()
    if not session:
        return
    if str(operator_content or "").strip():
        remember_turn(session, "user", operator_content)
    if str(agent_content or "").strip():
        remember_turn(session, "assistant", agent_content)


__all__ = ["remember_lane_b_turn"]
