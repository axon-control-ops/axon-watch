"""KAIRO persona voice lines for operator-facing copy."""

from __future__ import annotations


def build_persona_voice_line(
    *,
    pending_approvals: int,
    top_signal_title: str,
    degraded_active: bool,
    load_state: str = "loaded",
) -> str:
    if load_state == "loading":
        return "KAIRO: Standing by while briefing loads."
    if load_state == "error":
        return "KAIRO: Briefing unavailable. Check control-plane connectivity."

    if pending_approvals > 0:
        suffix = "" if pending_approvals == 1 else "s"
        return f"KAIRO: {pending_approvals} approval{suffix} need your review before I can continue."

    if top_signal_title.strip():
        return "KAIRO: Top signals need review. Tell me which workspace to focus."

    if degraded_active:
        return "KAIRO: Runtime is degraded. Review the status strip before continuing."

    return "KAIRO: I'm listening. Tell me what to focus on."
