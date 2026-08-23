"""Deterministic reply drafts for operator email triage (control-plane)."""

from __future__ import annotations

import re
from typing import Any

_ACTION_PATTERNS = (
    re.compile(
        r"\b(action required|please|kindly|provide|can you|could you|need to|follow up|review|confirm|send|update|fix)\b",
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

_QUOTE_BOUNDARY_RE = re.compile(
    r"(?im)^(?:_{5,}|-{2,}\s*original message\s*-{2,}|from:\s|sent:\s|to:\s|subject:\s|on .+wrote:)"
)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_BATCH_NUMBER_RE = re.compile(r"\bbatch\s+number\b", re.I)
_PRODUCT_AFTER_NAMELY_RE = re.compile(
    r"\bnamely\s+the\s+(.+?)(?:,|\s+in order\b|\s+so\b|\.|$)",
    re.I,
)


def _current_message_text(text: str) -> str:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return ""
    boundary = _QUOTE_BOUNDARY_RE.search(raw)
    if boundary:
        raw = raw[: boundary.start()].strip()
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if _QUOTE_BOUNDARY_RE.match(stripped):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _sender_greeting(sender: str) -> str:
    display = str(sender or "").split("<", 1)[0].strip().strip('"').strip()
    if not display:
        return "there"
    if "," in display:
        after_comma = display.split(",", 1)[1].strip()
        if after_comma:
            display = after_comma
    token = re.sub(r"[^A-Za-zÀ-ÿ'-]", "", display.split()[0] if display.split() else "")
    if not token:
        return "there"
    generic = {"cto", "ceo", "finance", "info", "support", "admin", "sales", "ops", "team"}
    if token.lower() in generic or token.isupper():
        return "there"
    return token


def _signature_lines(operator_name: str) -> list[str]:
    cleaned = " ".join(str(operator_name or "").split()).strip()
    if not cleaned or cleaned.lower() in {"axon operator", "operator", "vaxon", "axon-x"}:
        return ["Kind regards,"]
    return ["Kind regards,", cleaned]


def _extract_product(text: str, subject: str) -> str:
    haystack = f"{text}\n{subject}"
    match = _PRODUCT_AFTER_NAMELY_RE.search(haystack)
    if match:
        return " ".join(match.group(1).split()).strip(" .")
    quoted = re.search(r"\bproduct quoted(?:,|\s+)(.+?)(?:,|\s+in order\b|\.|$)", haystack, re.I)
    if quoted:
        return " ".join(quoted.group(1).split()).strip(" .")
    subject_match = re.search(
        r"\bquotation\s+submission:\s*(.+?)(?:\s+\(|\s+[—-]\s+|$)",
        subject,
        re.I,
    )
    if subject_match:
        return " ".join(subject_match.group(1).split()).strip(" .")
    return "the quoted product"


def _reply_for_current_ask(*, text: str, subject: str) -> list[str] | None:
    compact = " ".join(text.split())
    if _BATCH_NUMBER_RE.search(compact):
        product = _extract_product(compact, subject)
        addresses = _EMAIL_RE.findall(compact)
        destination = ""
        if addresses:
            unique = list(dict.fromkeys(addresses))
            destination = f" to both addresses you listed ({', '.join(unique[:2])})"
        return [
            "Thank you for the quotation.",
            "",
            (
                f"I’ll send through the batch number for {product}{destination}. "
                "If the supplier confirms a separate production batch or reference, "
                "I’ll include it clearly so you can verify the quoted item."
            ),
        ]
    return None


def suggest_email_reply(
    *,
    subject: str = "",
    sender: str = "",
    text: str = "",
    operator_name: str = "",
) -> dict[str, Any]:
    subject = str(subject or "").strip()
    sender = str(sender or "").strip()
    current_text = _current_message_text(str(text or ""))
    snippet = " ".join(current_text.split())[:240]
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
    greeting = _sender_greeting(sender)

    lines = [f"Hi {greeting},", ""]
    ask_reply = _reply_for_current_ask(text=current_text, subject=subject)
    if ask_reply:
        lines.extend(ask_reply)
    elif action == "reply_or_investigate":
        lines.append(
            "Thanks for flagging this — I am looking into it now and will come back with a concrete update."
        )
    elif action == "capture_follow_up":
        lines.append("Thanks for the note. I’ll work through this and come back with the requested update.")
    else:
        lines.append("Thanks for the update — I have reviewed the thread and will keep an eye on it.")
    if due_markers:
        lines.extend(["", f"Timing noted: {', '.join(due_markers[:3])}."])
    lines.extend(["", *_signature_lines(operator_name)])

    return {
        "reply_subject": reply_subject,
        "reply_body": "\n".join(lines).strip() + "\n",
        "to": sender,
        "recommended_action": action,
        "recommended_detail": detail,
    }
