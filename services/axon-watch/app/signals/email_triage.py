"""Deterministic email message analysis for watch inbox signals.

Ported from axon-local operator_email_triage.analyze_email_message only —
no DB, IMAP, or account collection.
"""

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
_COMMITMENT_PATTERNS = (
    re.compile(r"\b(i will|we will|i'll|we'll|committed to|promised to)\b", re.I),
)
_DUE_PATTERNS = re.compile(
    r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.I,
)


def _sentence_candidates(text: str) -> list[str]:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def analyze_email_message(
    message: dict[str, Any],
    *,
    workspace_names: list[str] | None = None,
) -> dict[str, Any]:
    """Extract deterministic tasks, risks, and commitments from an email."""

    subject = str(message.get("subject") or "").strip()
    sender = str(message.get("from") or "").strip()
    snippet = str(message.get("text") or message.get("snippet") or "").strip()
    combined = f"{subject}\n{snippet}".strip()
    sentences = _sentence_candidates(combined)

    actions = [
        sentence
        for sentence in sentences
        if any(pattern.search(sentence) for pattern in _ACTION_PATTERNS)
    ]
    risks = [
        sentence
        for sentence in sentences
        if any(pattern.search(sentence) for pattern in _RISK_PATTERNS)
    ]
    commitments = [
        sentence
        for sentence in sentences
        if any(pattern.search(sentence) for pattern in _COMMITMENT_PATTERNS)
    ]
    due_markers = sorted({match.group(0) for match in _DUE_PATTERNS.finditer(combined)})

    matched_workspaces: list[str] = []
    for workspace_name in workspace_names or []:
        candidate = str(workspace_name or "").strip()
        if candidate and candidate.lower() in combined.lower():
            matched_workspaces.append(candidate)

    priority = 20
    if actions:
        priority += 25
    if risks:
        priority += 35
    if commitments:
        priority += 15
    if due_markers:
        priority += 15
    priority = max(5, min(priority, 100))

    risk_level = "low"
    if priority >= 80 or len(risks) >= 2:
        risk_level = "high"
    elif priority >= 50:
        risk_level = "medium"

    if risks:
        recommended_action = "reply_or_investigate"
        recommended_detail = (
            "Respond to the blocker or investigate the issue mentioned in the email."
        )
    elif actions:
        recommended_action = "capture_follow_up"
        recommended_detail = (
            "Turn the requested follow-up into a tracked task and answer the sender."
        )
    elif commitments:
        recommended_action = "record_commitment"
        recommended_detail = (
            "Capture the commitment so Axon can remind you before it slips."
        )
    else:
        recommended_action = "monitor_email"
        recommended_detail = (
            "Keep this thread in view for context, but no urgent follow-up is obvious."
        )

    return {
        "message_id": str(message.get("message_id") or message.get("uid") or "").strip(),
        "account_id": str(message.get("account_id") or "").strip(),
        "account_email": str(message.get("account_email") or "").strip(),
        "subject": subject,
        "sender": sender,
        "snippet": snippet[:280],
        "priority": priority,
        "risk_level": risk_level,
        "action_requests": actions[:5],
        "risks": risks[:5],
        "commitments": commitments[:5],
        "due_markers": due_markers[:5],
        "workspace_hints": matched_workspaces[:5],
        "recommended_action": recommended_action,
        "recommended_detail": recommended_detail,
    }
