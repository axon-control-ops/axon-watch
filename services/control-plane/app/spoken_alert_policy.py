"""Policy for high-value spoken alerts from canonical briefing/signal truth."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

INTERRUPTIVE_MODES = frozenset({"approval", "execute"})

from app.operator_alert_explain import explain_operator_alert
from app.operator_persona_name import OPERATOR_PERSONA_PREFIX

# In-process cooldown/dedupe for proactive speech (not timer heartbeats).
_LAST_SPOKEN: dict[str, float] = {}
_DEFAULT_COOLDOWN_SECONDS = 90.0
_CRITICAL_COOLDOWN_SECONDS = 30.0


def default_operator_presence_settings() -> dict[str, bool | str | float]:
    return {
        "operator_persona_enabled": True,
        "spoken_alerts_enabled": True,
        "privacy_mode": False,
        "mobile_compact_preferred": True,
        "kairo_narration": "conversational",
        "ide_voice_strip_enabled": False,
        "hands_free_enabled": False,
        "proactive_duplex_enabled": False,
        "wake_word_listening_consent": False,
        "wake_word_listening_enabled": False,
        "wake_word_sensitivity": "medium",
        "quiet_hours_start": "",
        "quiet_hours_end": "",
        # axon-local parity defaults (desktop voice deck).
        "speech_rate": 1.0,
        "speech_pitch": 1.04,
        "azure_voice_id": "en-GB-RyanNeural",
        "stt_mode": "cloud",
        "voice_routing_mode": "template_first",
        "narrate_tool_progress": False,
    }


def _spoken_message(spoken: str, *, persona_enabled: bool) -> str:
    clean = str(spoken or "").strip()
    if not clean:
        return ""
    if persona_enabled and not clean.upper().startswith("VAXON"):
        return f"{OPERATOR_PERSONA_PREFIX}{clean}"
    return clean


def _parse_hhmm(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def in_quiet_hours(
    settings: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    start = _parse_hhmm(settings.get("quiet_hours_start"))
    end = _parse_hhmm(settings.get("quiet_hours_end"))
    if start is None or end is None or start == end:
        return False
    clock = now or datetime.now().astimezone()
    minutes = clock.hour * 60 + clock.minute
    if start < end:
        return start <= minutes < end
    # Overnight window (e.g. 22:00 → 07:00).
    return minutes >= start or minutes < end


def _dedupe_key(*, reason: str, signal_id: str | None) -> str:
    return f"{reason}|{signal_id or ''}"


def _cooldown_seconds(reason: str, severity: str) -> float:
    if reason == "operator_approval_required" or severity in {"critical", "high"}:
        return _CRITICAL_COOLDOWN_SECONDS
    return _DEFAULT_COOLDOWN_SECONDS


def should_suppress_duplicate(
    *,
    reason: str,
    signal_id: str | None,
    severity: str = "info",
    now_ts: float | None = None,
) -> bool:
    key = _dedupe_key(reason=reason, signal_id=signal_id)
    stamp = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    previous = _LAST_SPOKEN.get(key)
    if previous is None:
        return False
    return (stamp - previous) < _cooldown_seconds(reason, severity)


def mark_spoken_alert(
    *,
    reason: str,
    signal_id: str | None,
    now_ts: float | None = None,
) -> None:
    key = _dedupe_key(reason=reason, signal_id=signal_id)
    _LAST_SPOKEN[key] = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()


def clear_spoken_alert_dedupe_for_tests() -> None:
    _LAST_SPOKEN.clear()


def resolve_spoken_alert(
    *,
    settings: dict[str, bool],
    pending_approvals: int,
    top_signal: dict[str, object] | None,
    now: datetime | None = None,
    now_ts: float | None = None,
) -> dict[str, object]:
    persona_enabled = bool(settings.get("operator_persona_enabled", True))

    if settings.get("privacy_mode"):
        return {
            "eligible": False,
            "reason": "privacy_mode_active",
            "signal_id": None,
            "message": "",
            "explanation": None,
        }

    if not settings.get("spoken_alerts_enabled", True):
        return {
            "eligible": False,
            "reason": "spoken_alerts_disabled",
            "signal_id": None,
            "message": "",
            "explanation": None,
        }

    quiet = in_quiet_hours(settings, now=now)

    if pending_approvals > 0:
        reason = "operator_approval_required"
        if should_suppress_duplicate(reason=reason, signal_id=None, severity="critical", now_ts=now_ts):
            return {
                "eligible": False,
                "reason": "duplicate_suppressed",
                "signal_id": None,
                "message": "",
                "explanation": None,
            }
        explained = explain_operator_alert(
            pending_approvals=pending_approvals,
            reason=reason,
        )
        mark_spoken_alert(reason=reason, signal_id=None, now_ts=now_ts)
        return {
            "eligible": True,
            "reason": reason,
            "signal_id": None,
            "message": _spoken_message(explained["spoken"], persona_enabled=persona_enabled),
            "explanation": explained,
        }

    if not isinstance(top_signal, dict):
        return {
            "eligible": False,
            "reason": "no_interruptive_signal",
            "signal_id": None,
            "message": "",
            "explanation": None,
        }

    signal_id = str(top_signal.get("signal_id", "")).strip()
    severity = str(top_signal.get("severity", "info")).strip().lower()
    title = str(top_signal.get("title", "signal")).strip() or "signal"
    summary = str(top_signal.get("summary", "") or "").strip()
    meta = top_signal.get("meta")
    watch_rule = top_signal.get("watch_rule")
    rule = watch_rule if isinstance(watch_rule, dict) else {}
    mode = str(rule.get("mode", "observe")).strip().lower()
    interrupts = bool(rule.get("interrupts"))

    if mode in INTERRUPTIVE_MODES or (interrupts and severity in {"critical", "high"}):
        # Quiet hours mute high/execute chatter; critical still escalates once.
        if quiet and severity not in {"critical"}:
            return {
                "eligible": False,
                "reason": "quiet_hours",
                "signal_id": signal_id or None,
                "message": "",
                "explanation": None,
            }
        reason = str(rule.get("reason") or "high_urgency_signal")
        if should_suppress_duplicate(
            reason=reason,
            signal_id=signal_id or None,
            severity=severity,
            now_ts=now_ts,
        ):
            return {
                "eligible": False,
                "reason": "duplicate_suppressed",
                "signal_id": signal_id or None,
                "message": "",
                "explanation": None,
            }
        explained = explain_operator_alert(
            signal_id=signal_id,
            title=title,
            summary=summary,
            meta=meta if isinstance(meta, dict) else None,
            reason=reason,
        )
        mark_spoken_alert(reason=reason, signal_id=signal_id or None, now_ts=now_ts)
        return {
            "eligible": True,
            "reason": reason,
            "signal_id": signal_id or None,
            "message": _spoken_message(explained["spoken"], persona_enabled=persona_enabled),
            "explanation": explained,
        }

    return {
        "eligible": False,
        "reason": "no_interruptive_signal",
        "signal_id": signal_id or None,
        "message": "",
        "explanation": None,
    }
