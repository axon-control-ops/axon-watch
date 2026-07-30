"""Policy for high-value spoken alerts from canonical briefing/signal truth."""

from __future__ import annotations

import re

INTERRUPTIVE_MODES = frozenset({"approval", "execute"})

from app.operator_alert_explain import explain_operator_alert
from app.operator_persona_name import OPERATOR_PERSONA_PREFIX


def default_operator_presence_settings() -> dict[str, bool | str | float]:
    return {
        "operator_persona_enabled": True,
        "spoken_alerts_enabled": True,
        "privacy_mode": False,
        "mobile_compact_preferred": True,
        "kairo_narration": "conversational",
        "ide_voice_strip_enabled": False,
        # Hands-free stays opt-in (mic permission). Duplex = speak then listen like JARVIS.
        "hands_free_enabled": False,
        "proactive_duplex_enabled": True,
        # manual = alerts only; semi = VAXON advisory; full = advisory + continuous workers.
        "autonomy_mode": "manual",
        # axon-local parity defaults (desktop voice deck).
        "speech_rate": 1.0,
        "speech_pitch": 1.04,
        "azure_voice_id": "en-GB-RyanNeural",
        "stt_mode": "cloud",
        # Prefer runtime for deep status/open asks; keep templates for quick facts.
        "voice_routing_mode": "runtime_on_deep",
        # Operator-global VAXON model — independent from workspace Composer prefs.
        "vaxon_model_id": "cursor-grok-4.5-high-fast",
        "narrate_tool_progress": False,
    }


def _spoken_message(spoken: str, *, persona_enabled: bool) -> str:
    clean = str(spoken or "").strip()
    if not clean:
        return ""
    if persona_enabled and not clean.upper().startswith("VAXON"):
        return f"{OPERATOR_PERSONA_PREFIX}{clean}"
    return clean


def resolve_spoken_alert(
    *,
    settings: dict[str, bool],
    pending_approvals: int,
    top_signal: dict[str, object] | None,
    degraded_active: bool = False,
    degraded_reason: str | None = None,
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

    if pending_approvals > 0:
        explained = explain_operator_alert(
            pending_approvals=pending_approvals,
            reason="operator_approval_required",
        )
        return {
            "eligible": True,
            "reason": "operator_approval_required",
            "signal_id": None,
            "message": _spoken_message(explained["spoken"], persona_enabled=persona_enabled),
            "explanation": explained,
        }

    if degraded_active:
        detail = str(degraded_reason or "").strip() or "runtime health check failed"
        public_only = bool(
            re.search(
                r"public health|host unreachable|axon\.edudashpro|remote ingress",
                detail,
                re.I,
            )
        )
        explained = explain_operator_alert(
            title="Runtime degraded",
            summary=detail,
            reason="runtime_degraded",
        )
        if public_only:
            explained = {
                **explained,
                "spoken": (
                    "Sir, public tunnel health is degraded, but local Axon-X is up. "
                    "Local charters can continue. Want me to repair the tunnel, or proceed?"
                ),
                "you_do": (
                    "You can keep working locally. Optional: repair Cloudflare DNS/tunnel "
                    "for axon.edudashpro.org.za, or ask VAXON to proceed with a charter."
                ),
            }
        return {
            "eligible": True,
            "reason": "runtime_degraded",
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
        explained = explain_operator_alert(
            signal_id=signal_id,
            title=title,
            summary=summary,
            meta=meta if isinstance(meta, dict) else None,
            reason=str(rule.get("reason") or "high_urgency_signal"),
        )
        return {
            "eligible": True,
            "reason": str(rule.get("reason") or "high_urgency_signal"),
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
