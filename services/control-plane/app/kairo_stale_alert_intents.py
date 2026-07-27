"""VAXON early intent: confirm and clear stale / useless Attention alerts."""

from __future__ import annotations

import re
from typing import Any

from app.kairo_participant_memory import apply_participant_address, get_active_participant

_CLEAR_STALE_RE = re.compile(
    r"\b("
    r"clear\s+(?:the\s+)?(?:stale|useless|old)\s+(?:alert|alerts|error|errors|signal|signals)"
    r"|clear\s+stale"
    r"|dismiss\s+(?:the\s+)?(?:stale|drill|useless)\s+(?:alert|alerts|error|errors|fast\s*gate)?"
    r"|acknowledge\s+(?:the\s+)?(?:stale|old)\s+(?:alert|alerts|signal|signals)"
    r"|clear\s+(?:that\s+)?(?:drill|fast\s*gate)\s+(?:alert|error|signal)?"
    r"|clean\s+up\s+(?:stale\s+)?(?:alerts|errors|signals)"
    r")\b",
    re.IGNORECASE,
)


def detect_clear_stale_alerts_intent(content: str) -> bool:
    return bool(_CLEAR_STALE_RE.search(str(content or "")))


def maybe_handle_clear_stale_alerts_intent(
    *,
    content: str,
    session_id: str,
    guest_name: str | None,
) -> dict[str, Any] | None:
    if not detect_clear_stale_alerts_intent(content):
        return None

    from app.ci_remediation.stale_sweep import sweep_stale_ci_signals

    result = sweep_stale_ci_signals(include_drills=True, confirm_with_gh=True)
    cleared = int(result.get("resolved_count") or 0)
    ids = [str(item) for item in (result.get("resolved_signal_ids") or []) if str(item).strip()]
    participant = guest_name or get_active_participant(session_id)

    if cleared <= 0:
        reply = (
            "I checked Attention for stale Fast Gate / CI alerts. "
            "Nothing looked confirmed-stale yet — live reds stay until the branch is green "
            "or you acknowledge a specific signal."
        )
    else:
        sample = ", ".join(ids[:3])
        more = f" (+{cleared - 3} more)" if cleared > 3 else ""
        reply = (
            f"Confirmed stale or useless — cleared {cleared} CI alert(s)"
            f"{f' including {sample}{more}' if sample else ''}. "
            "Drill branches and superseded Fast Gate failures are gone from Attention."
        )

    return {
        "turn_kind": "action",
        "reply": apply_participant_address(reply, participant),
        "source": "template",
        "command_content": None,
        "action": {
            "type": "clear_stale_ci_alerts",
            "resolved_count": cleared,
            "resolved_signal_ids": ids,
        },
        "artifacts": [],
        "active_participant": participant,
        "action_tier": "reversible_auto",
    }
