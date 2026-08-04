"""Next-move selection for deterministic operator REPORT."""

from __future__ import annotations

import re
from typing import Any

from app.kairo.report_text import _scrub_operator_line, push_failure_next_move


def degraded_reasons(snapshot: dict[str, Any]) -> list[str]:
    degraded = (snapshot.get("briefing") or {}).get("degraded") or {}
    if not isinstance(degraded, dict):
        return []
    raw = degraded.get("reasons") or []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def remote_ingress_soft(snapshot: dict[str, Any]) -> bool:
    degraded = (snapshot.get("briefing") or {}).get("degraded") or {}
    if not isinstance(degraded, dict) or not degraded.get("active"):
        return False
    joined = " ".join(degraded_reasons(snapshot)).lower()
    if not joined:
        return True
    markers = (
        "tunnel",
        "remote ingress",
        "edudashpro",
        "public health",
        "network unreachable",
        "host unreachable",
        "name or service not known",
    )
    return any(marker in joined for marker in markers)


def handoff_push_failure_next_move(snapshot: dict[str, Any]) -> str | None:
    for handoff in snapshot.get("handoffs") or []:
        if not isinstance(handoff, dict):
            continue
        raw = " ".join(
            [
                str(handoff.get("headline") or ""),
                str(handoff.get("lead_summary") or ""),
                str(handoff.get("lead_next") or ""),
            ]
        )
        next_move = push_failure_next_move(raw)
        if next_move:
            return next_move
    return None


def signal_next_move(snapshot: dict[str, Any]) -> str | None:
    for signal in (snapshot.get("top_signals") or [])[:3]:
        if not isinstance(signal, dict):
            continue
        title = str(signal.get("title") or "").strip()
        summary = str(signal.get("summary") or "").strip()
        hay = f"{title} {summary}".lower()
        if not title:
            continue
        if "github" in hay and (
            "token" in hay
            or "401" in hay
            or "placeholder" in hay
            or "probe" in hay
            or "api warning" in hay
        ):
            return "I'll open Vault and restore the GitHub probe token next"
        if "sentry" in hay:
            return f"VAXON is investigating {title} and will report back here"
        severity = str(signal.get("severity") or "").strip().lower()
        if severity in {"critical", "high"}:
            return f"VAXON is investigating {title} and will report back here"
    return None


def next_move(snapshot: dict[str, Any]) -> str:
    pending = int(snapshot.get("pending_approvals") or 0)
    if pending > 0:
        return "I'll clear Approvals before starting anything new"

    if remote_ingress_soft(snapshot):
        return "I'll restart the public tunnel next"

    push_next_move = handoff_push_failure_next_move(snapshot)
    if push_next_move:
        return push_next_move

    signal_move = signal_next_move(snapshot)
    if signal_move:
        return signal_move

    advise = str((snapshot.get("briefing") or {}).get("advise") or "").strip().rstrip(".")
    if advise:
        advise_clean = _scrub_operator_line(advise, max_len=160)
        lower = advise_clean.lower()
        if lower.startswith(("i'd", "i'll", "i will")):
            return advise_clean
        if lower.startswith("vaxon is attending") or lower.startswith("vaxon owns"):
            target = re.search(
                r"\b(?:in|for)\s+([A-Za-z0-9][A-Za-z0-9 _-]{0,40})\b",
                advise_clean,
                re.IGNORECASE,
            )
            if target:
                name = target.group(1).strip().rstrip("—,").strip()
                if name:
                    return f"VAXON is investigating {name} and will report back here"
            return "VAXON is investigating that signal and will report back here"
        if "needs review" in lower and "switch" in lower:
            target = re.search(r"\bsignal in ([a-z0-9_-]+)\b", advise_clean, re.IGNORECASE)
            return (
                f"VAXON is investigating the signal in {target.group(1)} "
                "and will report back here"
                if target
                else "VAXON is investigating that signal and will report back here"
            )
        if "github" in lower and ("token" in lower or "vault" in lower or "api" in lower):
            return "I'll open Vault and restore the GitHub probe token next"
        if "lead" in lower and ("rollup" in lower or "open" in lower):
            return "I'll open the Lead rollup and walk the next handoff"
        if "approval" in lower:
            return "I'll clear Approvals before starting anything new"
        if "tunnel" in lower or "remote ingress" in lower or "public health" in lower:
            return "I'll restart the public tunnel next"
        if lower.startswith("inspect "):
            target = advise_clean[8:].strip() or "that signal"
            return f"VAXON is investigating {target} and will report back here"
        if "sentry" in lower:
            return f"VAXON is investigating {advise_clean} and will report back here"
        return f"I'll open Attention for {advise_clean}"
    for handoff in snapshot.get("handoffs") or []:
        lead_next = _scrub_operator_line(str(handoff.get("lead_next") or ""), max_len=140)
        if lead_next:
            return f"I'll take the next Lead decision: {lead_next}"
    awaiting = int(snapshot.get("awaiting_engagement_count") or 0)
    if awaiting > 0:
        return "I'll open Mission Control for the Lead rollup"
    actions = snapshot.get("next_safe_actions") or []
    if actions:
        label = str(actions[0].get("label") or actions[0].get("title") or "").strip()
        if label:
            return f"I'll {label[0].lower() + label[1:]}" if label[0].isupper() else f"I'll {label}"
    return "I'll keep watching — say the word if you want DashPro, Approvals, or a fleet roll"
