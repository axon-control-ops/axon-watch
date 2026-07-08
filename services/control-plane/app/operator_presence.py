"""Operator presence projection: persona copy, spoken-alert eligibility, mobile posture."""

from __future__ import annotations

from app.kairo_persona import build_persona_voice_line
from app.operator_briefing_signals import first_actionable_signal, is_bootstrap_signal
from app.spoken_alert_policy import (
    default_operator_presence_settings,
    resolve_spoken_alert,
)


def resolve_presence_state(
    *,
    settings: dict[str, bool],
    pending_approvals: int,
    critical_signals: int,
    high_signals: int,
    watch_connected: bool,
    briefing_loaded: bool,
) -> str:
    if settings.get("privacy_mode"):
        return "privacy_blocked"
    if pending_approvals > 0 or critical_signals > 0 or high_signals > 0:
        return "alerting"
    if briefing_loaded and watch_connected:
        return "observing"
    return "idle"


def build_operator_presence(
    briefing: dict[str, object],
    *,
    viewport_compact: bool = False,
    settings: dict[str, bool] | None = None,
) -> dict[str, object]:
    resolved_settings = dict(default_operator_presence_settings())
    if settings:
        resolved_settings.update(settings)

    top_signals = briefing.get("top_signals", [])
    top_signal = first_actionable_signal(top_signals)
    if top_signal is None and isinstance(top_signals, list) and top_signals:
        # Fall back to first non-bootstrap signal for spoken-alert policy only.
        for item in top_signals:
            if isinstance(item, dict) and not is_bootstrap_signal(item):
                top_signal = item
                break

    pending_approvals = int(
        (briefing.get("pending_approvals") or {}).get("count", 0)  # type: ignore[union-attr]
        if isinstance(briefing.get("pending_approvals"), dict)
        else 0
    )
    degraded = briefing.get("degraded")
    degraded_active = bool(degraded.get("active")) if isinstance(degraded, dict) else False
    connectivity = briefing.get("connectivity")
    watch_connected = (
        bool(connectivity.get("watch_connected"))
        if isinstance(connectivity, dict)
        else False
    )

    critical_count = sum(
        1
        for item in (top_signals if isinstance(top_signals, list) else [])
        if isinstance(item, dict) and str(item.get("severity", "")).lower() == "critical"
    )
    high_count = sum(
        1
        for item in (top_signals if isinstance(top_signals, list) else [])
        if isinstance(item, dict) and str(item.get("severity", "")).lower() == "high"
    )

    spoken_alert = resolve_spoken_alert(
        settings=resolved_settings,
        pending_approvals=pending_approvals,
        top_signal=top_signal,
    )
    voice_line = build_persona_voice_line(
        pending_approvals=pending_approvals,
        top_signal_title=str(top_signal.get("title", "")) if top_signal else "",
        degraded_active=degraded_active,
        persona_enabled=bool(resolved_settings.get("operator_persona_enabled", True)),
    )
    presence_state = resolve_presence_state(
        settings=resolved_settings,
        pending_approvals=pending_approvals,
        critical_signals=critical_count,
        high_signals=high_count,
        watch_connected=watch_connected,
        briefing_loaded=True,
    )

    compact_layout = bool(viewport_compact)

    return {
        "persona_voice_line": voice_line,
        "presence_state": presence_state,
        "settings": resolved_settings,
        "spoken_alert": spoken_alert,
        "mobile": {
            "compact_layout": compact_layout,
            "foreground_only": True,
        },
    }
