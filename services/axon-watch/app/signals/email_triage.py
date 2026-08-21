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
_HARD_RISK_PATTERNS = (
    re.compile(
        r"\b(urgent|asap|blocked|can't|cannot|failure|failing|overdue|escalat)\w*\b",
        re.I,
    ),
)
# Soft risk words often appear in marketing copy ("deadline", contest cutoffs).
_SOFT_RISK_PATTERNS = (
    re.compile(r"\bdeadline\w*\b", re.I),
)
_COMMITMENT_PATTERNS = (
    re.compile(r"\b(i will|we will|i'll|we'll|committed to|promised to)\b", re.I),
)
# Avoid bare "may" — it matches the English modal verb more often than the month.
_DUE_PATTERNS = re.compile(
    r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|june?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.I,
)
_DUE_MAY_MONTH = re.compile(r"\bMay\b")
_PROMO_PATTERNS = (
    re.compile(
        r"\b(unsubscribe|view in browser|pre-?register|devpost|hackathon|"
        r"in prizes?|prize categor(?:y|ies)|weeks to build|newsletter|"
        r"limited[- ]time offer|promo(?:tion)?|utm_|shipaton)\b",
        re.I,
    ),
    re.compile(r"customer\.io|mailchimp\.com|sendgrid\.net|list-manage\.com", re.I),
)
_PROMO_PRIORITY_CAP = 40
_AUTOMATED_SENDER_PATTERNS = (
    re.compile(r"noreply|no-reply|do-not-reply|donotreply|billing-noreply", re.I),
)
# Any address shaped like this cannot receive a reply -- it either bounces or
# is discarded server-side. This used to be consulted only inside the two
# narrow billing/dev-notification checks below, so a no-reply sender whose
# body did not also look like a billing or CI notice (a GitHub "action
# required: 2FA" account notice, for instance) fell through to ordinary
# action detection and got a full drafted reply addressed to it.
_NO_REPLY_SENDER_PATTERNS = _AUTOMATED_SENDER_PATTERNS + (
    re.compile(r"\bmailer-daemon\b", re.I),
    re.compile(r"\bpostmaster@", re.I),
)


def is_no_reply_sender(sender: str) -> bool:
    """True when a reply cannot reach a person at this address at all."""
    return any(pattern.search(str(sender or "")) for pattern in _NO_REPLY_SENDER_PATTERNS)
_BILLING_NOTICE_PATTERNS = (
    re.compile(
        r"\b(invoice\s+\S+\s+is\s+ready|your\s+\w*\s*invoice|your\s+statement\s+is\s+ready|"
        r"payment\s+receipt|billing\s+statement|amount\s+due|disregard\s+this\s+email)\b",
        re.I,
    ),
)
_LOW_ATTENTION_PRIORITY_CAP = 40
_DEV_NOTIFICATION_PATTERNS = (
    re.compile(r"\b(run failed|workflow run|check[- ]suite|github actions)\b", re.I),
    re.compile(r"\bvercel\[bot\].*\b(?:pull|pr)\b", re.I | re.S),
)


def _is_promotional_email(*, subject: str, sender: str, snippet: str) -> bool:
    combined = f"{subject}\n{sender}\n{snippet}"
    return any(pattern.search(combined) for pattern in _PROMO_PATTERNS)


def _is_automated_billing_notice(*, subject: str, sender: str, snippet: str) -> bool:
    """Detect vendor noreply invoice/billing mail that should not page the inbox."""
    combined = f"{subject}\n{sender}\n{snippet}"
    has_automated_sender = any(pattern.search(sender) for pattern in _AUTOMATED_SENDER_PATTERNS)
    has_billing_copy = any(pattern.search(combined) for pattern in _BILLING_NOTICE_PATTERNS)
    return has_automated_sender and has_billing_copy


def _is_automated_dev_notification(*, subject: str, sender: str, snippet: str) -> bool:
    """Detect CI/deploy mail already represented by native engineering signals."""
    combined = f"{sender}\n{subject}\n{snippet}"
    automated = any(pattern.search(sender) for pattern in _AUTOMATED_SENDER_PATTERNS) or any(
        marker in sender.lower() for marker in ("notifications@github.com", "vercel[bot]")
    )
    return automated and any(pattern.search(combined) for pattern in _DEV_NOTIFICATION_PATTERNS)


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

    promotional = _is_promotional_email(subject=subject, sender=sender, snippet=snippet)
    automated_billing = _is_automated_billing_notice(
        subject=subject,
        sender=sender,
        snippet=snippet,
    )
    automated_dev_notification = _is_automated_dev_notification(
        subject=subject, sender=sender, snippet=snippet
    )
    # Catches every other shape of no-reply mail the two narrow checks above
    # miss -- account/security notices, password resets, order confirmations --
    # anything from an address a reply cannot reach.
    no_reply_sender = is_no_reply_sender(sender) and not (
        automated_billing or automated_dev_notification
    )
    low_attention = promotional or automated_billing or automated_dev_notification or no_reply_sender
    risk_patterns = _HARD_RISK_PATTERNS if low_attention else (_HARD_RISK_PATTERNS + _SOFT_RISK_PATTERNS)

    actions = [
        sentence
        for sentence in sentences
        if any(pattern.search(sentence) for pattern in _ACTION_PATTERNS)
    ]
    risks = [
        sentence
        for sentence in sentences
        if any(pattern.search(sentence) for pattern in risk_patterns)
    ]
    commitments = [
        sentence
        for sentence in sentences
        if any(pattern.search(sentence) for pattern in _COMMITMENT_PATTERNS)
    ]
    due_markers = sorted({match.group(0) for match in _DUE_PATTERNS.finditer(combined)})
    for match in _DUE_MAY_MONTH.finditer(combined):
        token = match.group(0)
        if token not in due_markers:
            due_markers.append(token)
    due_markers = sorted(due_markers, key=str.lower)

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
    if promotional:
        # Marketing / contest mail should not drown out real blockers.
        priority = min(priority, _LOW_ATTENTION_PRIORITY_CAP)
        risks = []
        commitments = []
    elif automated_billing or automated_dev_notification or no_reply_sender:
        # Vendor noreply invoices use "review" boilerplate — not a human follow-up.
        priority = min(priority, _LOW_ATTENTION_PRIORITY_CAP)
        risks = []
        commitments = []
        actions = []
    priority = max(5, min(priority, 100))

    risk_level = "low"
    if priority >= 80 or len(risks) >= 2:
        risk_level = "high"
    elif priority >= 50:
        risk_level = "medium"

    if promotional:
        recommended_action = "monitor_email"
        recommended_detail = (
            "Promotional or contest email — keep for awareness, not as an urgent blocker."
        )
    elif automated_billing:
        recommended_action = "monitor_email"
        recommended_detail = (
            "Automated billing or invoice notice — check your vendor portal; no reply expected."
        )
    elif no_reply_sender:
        recommended_action = "monitor_email"
        recommended_detail = (
            "Sender does not accept replies (no-reply address) — no draft is suggested."
        )
    elif automated_dev_notification:
        recommended_action = "monitor_engineering_signal"
        recommended_detail = "Automated CI/deploy mail is covered by the native engineering signal."
    elif risks:
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
        "promotional": promotional,
        "automated_billing": automated_billing,
        "automated_dev_notification": automated_dev_notification,
        "no_reply_sender": no_reply_sender,
        "action_requests": actions[:5],
        "risks": risks[:5],
        "commitments": commitments[:5],
        "due_markers": due_markers[:5],
        "workspace_hints": matched_workspaces[:5],
        "recommended_action": recommended_action,
        "recommended_detail": recommended_detail,
    }
