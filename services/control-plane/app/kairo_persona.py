"""VAXON persona voice lines for operator-facing copy."""

from __future__ import annotations

from app.operator_persona_name import OPERATOR_PERSONA_PREFIX


def _workspace_focus_label(workspace_id: str) -> str:
    clean = str(workspace_id or "").strip()
    if not clean:
        return ""
    if clean.startswith("workspace_"):
        clean = clean[len("workspace_") :]
    return clean.replace("_", " ").strip() or str(workspace_id).strip()


def build_persona_voice_line(
    *,
    pending_approvals: int,
    top_signal_title: str,
    degraded_active: bool,
    load_state: str = "loaded",
    persona_enabled: bool = True,
    top_signal_workspace_id: str = "",
    top_signal_summary: str = "",
) -> str:
    """Build a short presence line from live briefing facts (not a generic canned ask)."""
    prefix = OPERATOR_PERSONA_PREFIX if persona_enabled else ""

    if load_state == "loading":
        return (
            f"{prefix}Standing by while briefing loads, sir."
            if persona_enabled
            else "Standing by while briefing loads."
        )
    if load_state == "error":
        return (
            f"{prefix}Briefing unavailable, sir. Check control-plane connectivity."
            if persona_enabled
            else "Briefing unavailable. Check control-plane connectivity."
        )

    if pending_approvals > 0:
        suffix = "" if pending_approvals == 1 else "s"
        return (
            f"{prefix}{pending_approvals} approval{suffix} need your review before I can continue, sir."
            if persona_enabled
            else f"{pending_approvals} approval{suffix} need your review before execution can continue."
        )

    title = top_signal_title.strip()
    if title:
        workspace = _workspace_focus_label(top_signal_workspace_id)
        summary = top_signal_summary.strip()
        detail = f"{title} — {summary}" if summary and summary.lower() not in title.lower() else title
        if workspace:
            return (
                f"{prefix}Top signal on {workspace}, sir — {detail}."
                if persona_enabled
                else f"Top signal on {workspace}: {detail}."
            )
        return (
            f"{prefix}Top signal needs review, sir — {detail}."
            if persona_enabled
            else f"Top signal needs review: {detail}."
        )

    if degraded_active:
        return (
            f"{prefix}Runtime is degraded, sir. Review the status strip before continuing."
            if persona_enabled
            else "Runtime is degraded. Review the status strip before continuing."
        )

    return (
        f"{prefix}I'm listening, sir. Tell me what to focus on."
        if persona_enabled
        else "Ready. Tell me what to focus on."
    )
