"""KAIRO persona voice lines for operator-facing copy."""

from __future__ import annotations


from app.operator_persona_name import OPERATOR_PERSONA_NAME, OPERATOR_PERSONA_PREFIX


def build_persona_voice_line(
    *,
    pending_approvals: int,
    top_signal_title: str,
    degraded_active: bool,
    load_state: str = "loaded",
    persona_enabled: bool = True,
) -> str:
    prefix = OPERATOR_PERSONA_PREFIX if persona_enabled else ""

    if load_state == "loading":
        return (
            f"{prefix}Standing by while briefing loads."
            if persona_enabled
            else "Standing by while briefing loads."
        )
    if load_state == "error":
        return (
            f"{prefix}Briefing unavailable. Check control-plane connectivity."
            if persona_enabled
            else "Briefing unavailable. Check control-plane connectivity."
        )

    if pending_approvals > 0:
        suffix = "" if pending_approvals == 1 else "s"
        return (
            f"{prefix}{pending_approvals} approval{suffix} need your review before I can continue."
            if persona_enabled
            else f"{pending_approvals} approval{suffix} need your review before execution can continue."
        )

    if top_signal_title.strip():
        return (
            f"{prefix}Top signals need review. Tell me which workspace to focus."
            if persona_enabled
            else "Top signals need review. Choose a workspace to focus."
        )

    if degraded_active:
        return (
            f"{prefix}Runtime is degraded. Review the status strip before continuing."
            if persona_enabled
            else "Runtime is degraded. Review the status strip before continuing."
        )

    return (
        f"{prefix}I'm listening. Tell me what to focus on."
        if persona_enabled
        else "Ready. Tell me what to focus on."
    )
