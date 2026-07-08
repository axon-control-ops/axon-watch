"""Policy for high-value spoken alerts from canonical briefing/signal truth."""

from __future__ import annotations

INTERRUPTIVE_MODES = frozenset({"approval", "execute"})


from app.operator_persona_name import OPERATOR_PERSONA_NAME, OPERATOR_PERSONA_PREFIX


def default_operator_presence_settings() -> dict[str, bool | str]:
    return {
        "operator_persona_enabled": True,
        "spoken_alerts_enabled": True,
        "privacy_mode": False,
        "mobile_compact_preferred": True,
        "kairo_narration": "conversational",
        "ide_voice_strip_enabled": False,
        "hands_free_enabled": False,
    }


def resolve_spoken_alert(
    *,
    settings: dict[str, bool],
    pending_approvals: int,
    top_signal: dict[str, object] | None,
) -> dict[str, object]:
    if settings.get("privacy_mode"):
        return {
            "eligible": False,
            "reason": "privacy_mode_active",
            "signal_id": None,
            "message": "",
        }

    if not settings.get("spoken_alerts_enabled", True):
        return {
            "eligible": False,
            "reason": "spoken_alerts_disabled",
            "signal_id": None,
            "message": "",
        }

    if pending_approvals > 0:
        suffix = "" if pending_approvals == 1 else "s"
        return {
            "eligible": True,
            "reason": "operator_approval_required",
            "signal_id": None,
            "message": f"{OPERATOR_PERSONA_PREFIX}{pending_approvals} approval{suffix} waiting for your review.",
        }

    if not isinstance(top_signal, dict):
        return {
            "eligible": False,
            "reason": "no_interruptive_signal",
            "signal_id": None,
            "message": "",
        }

    signal_id = str(top_signal.get("signal_id", "")).strip()
    severity = str(top_signal.get("severity", "info")).strip().lower()
    title = str(top_signal.get("title", "signal")).strip() or "signal"
    watch_rule = top_signal.get("watch_rule")
    rule = watch_rule if isinstance(watch_rule, dict) else {}
    mode = str(rule.get("mode", "observe")).strip().lower()
    interrupts = bool(rule.get("interrupts"))

    if mode in INTERRUPTIVE_MODES or (interrupts and severity in {"critical", "high"}):
        return {
            "eligible": True,
            "reason": str(rule.get("reason") or "high_urgency_signal"),
            "signal_id": signal_id or None,
            "message": f"{OPERATOR_PERSONA_NAME} attention: {title}.",
        }

    return {
        "eligible": False,
        "reason": "no_interruptive_signal",
        "signal_id": signal_id or None,
        "message": "",
    }
