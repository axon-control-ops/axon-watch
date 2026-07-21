"""VAXON persona voice lines for operator-facing copy."""

from __future__ import annotations

from typing import Any

from app.operator_alert_explain import explain_operator_alert
from app.operator_persona_name import OPERATOR_PERSONA_PREFIX


def build_persona_voice_line(
    *,
    pending_approvals: int,
    top_signal_title: str,
    degraded_active: bool,
    load_state: str = "loaded",
    persona_enabled: bool = True,
    top_signal_workspace_id: str = "",
    top_signal_summary: str = "",
    top_signal_id: str = "",
    top_signal_meta: dict[str, Any] | None = None,
) -> str:
    """Build a short presence line in plain English for the operator."""
    prefix = OPERATOR_PERSONA_PREFIX if persona_enabled else ""

    if load_state == "loading":
        return (
            f"{prefix}Hang on — I'm still getting your status ready."
            if persona_enabled
            else "Hang on — status is still loading."
        )
    if load_state == "error":
        return (
            f"{prefix}I can't reach the status service right now. Check that Axon is running."
            if persona_enabled
            else "Can't reach the status service. Check that Axon is running."
        )

    if pending_approvals > 0:
        explained = explain_operator_alert(
            pending_approvals=pending_approvals,
            reason="operator_approval_required",
        )
        spoken = explained["spoken"]
        return f"{prefix}{spoken}" if persona_enabled else spoken

    title = top_signal_title.strip()
    if title:
        meta = dict(top_signal_meta or {})
        if top_signal_workspace_id and "workspace_id" not in meta:
            meta["workspace_id"] = top_signal_workspace_id
        explained = explain_operator_alert(
            signal_id=top_signal_id,
            title=title,
            summary=top_signal_summary,
            meta=meta or None,
        )
        spoken = explained["spoken"]
        return f"{prefix}{spoken}" if persona_enabled else spoken

    if degraded_active:
        explained = explain_operator_alert(
            title="Runtime degraded",
            summary="Runtime is degraded",
            signal_id="signal_runtime_degraded",
        )
        spoken = explained["spoken"]
        return f"{prefix}{spoken}" if persona_enabled else spoken

    return (
        f"{prefix}I'm listening. Tell me what to focus on."
        if persona_enabled
        else "Ready. Tell me what to focus on."
    )
