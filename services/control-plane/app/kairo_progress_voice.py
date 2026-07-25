"""Progress-specific spoken fallback copy."""

from __future__ import annotations

from typing import Any

PROGRESS_FALLBACK_POOLS: dict[str, list[str]] = {
    "run_started": [
        "Understood, sir — I'll take care of that.",
        "Right, sir — leave it with me.",
        "Very good, sir — I'll see to it now.",
        "At once, sir — I'll handle that.",
        "Consider it in hand, sir.",
    ],
    "research_started": [
        "I'm checking the available evidence now.",
        "I'm reconciling the relevant evidence now.",
    ],
    "research_complete": [
        "I've finished checking the evidence.",
        "The evidence pass is complete.",
    ],
    "approval_required": [
        "I need your approval before I can continue.",
    ],
    "verified_complete": [
        "I've verified the result and it's ready for review.",
        "The result is verified and ready for you.",
    ],
    "unverified_complete": [
        "I have a result, but it still needs verification.",
    ],
    "stream_error": [
        "That run hit an error before completion.",
    ],
}

PROGRESS_EVENT_TYPES = frozenset(PROGRESS_FALLBACK_POOLS)


def contextual_progress_fallback(event_type: str, context: dict[str, Any]) -> str | None:
    query = str(context.get("research_query") or "").strip()
    warning = str(context.get("warning_summary") or "").strip()
    failure = str(context.get("failure_summary") or "").strip()
    if event_type == "research_started":
        return (
            f"I'm checking {query} against the available evidence now."
            if query
            else "I'm checking the available evidence now."
        )
    if event_type == "research_complete":
        return f"I've finished checking {query}." if query else "I've finished checking the evidence."
    if event_type == "approval_required":
        return "I need your approval before I can continue."
    if event_type == "verified_complete":
        return "I've verified the result and it's ready for review."
    if event_type == "unverified_complete":
        if warning:
            return f"I have a result, but it still needs verification: {warning}"
        return "I have a result, but it still needs verification before I call it done."
    if event_type == "stream_error":
        return f"That run hit an error: {failure}" if failure else "That run hit an error before completion."
    return None

