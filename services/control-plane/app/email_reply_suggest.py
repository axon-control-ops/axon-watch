"""Deterministic reply drafts for operator email triage (control-plane)."""

from __future__ import annotations

import re
from typing import Any

_ACTION_PATTERNS = (
    re.compile(
        r"\b(action required|please|can you|could you|need to|follow up|review|confirm|send|update|fix)\b",
        re.I,
    ),
)
_RISK_PATTERNS = (
    re.compile(
        r"\b(urgent|asap|blocked|can't|cannot|failure|failing|deadline|overdue|escalat)\w*\b",
        re.I,
    ),
)
_DUE_PATTERNS = re.compile(
    r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.I,
)


def suggest_email_reply(
    *,
    subject: str = "",
    sender: str = "",
    text: str = "",
    operator_name: str = "Axon operator",
) -> dict[str, Any]:
    subject = str(subject or "").strip()
    sender = str(sender or "").strip()
    snippet = " ".join(str(text or "").split())[:240]
    combined = f"{subject}\n{snippet}".strip()
    has_action = any(pattern.search(combined) for pattern in _ACTION_PATTERNS)
    has_risk = any(pattern.search(combined) for pattern in _RISK_PATTERNS)
    due_markers = sorted({match.group(0) for match in _DUE_PATTERNS.finditer(combined)})

    if has_risk:
        action = "reply_or_investigate"
        detail = "Respond to the blocker or investigate the issue mentioned in the email."
    elif has_action:
        action = "capture_follow_up"
        detail = "Turn the requested follow-up into a tracked task and answer the sender."
    else:
        action = "monitor_email"
        detail = "Keep this thread in view for context, but no urgent follow-up is obvious."

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject or '(no subject)'}"
    greeting = sender.split("<", 1)[0].strip().strip('"') or "there"
    if "," in greeting:
        greeting = greeting.split(",", 1)[0].strip()
    greeting = greeting.split()[0] if greeting else "there"

    lines = [f"Hi {greeting},", ""]
    if action == "reply_or_investigate":
        lines.append(
            "Thanks for flagging this — I am looking into it now and will come back with a concrete update."
        )
    elif action == "capture_follow_up":
        lines.append("Thanks for the note. I have captured the follow-up and will action it.")
    else:
        lines.append("Thanks for the update — I have reviewed the thread and will keep an eye on it.")
    if due_markers:
        lines.extend(["", f"Timing noted: {', '.join(due_markers[:3])}."])
    if snippet and action != "monitor_email":
        lines.extend(["", f"Regarding: {snippet[:180]}"])
    lines.extend(["", "Best regards,", operator_name])

    return {
        "reply_subject": reply_subject,
        "reply_body": "\n".join(lines).strip() + "\n",
        "to": sender,
        "recommended_action": action,
        "recommended_detail": detail,
    }
