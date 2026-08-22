"""Deterministic reply drafts for triaged operator email."""

from __future__ import annotations

import re
from typing import Any

_BATCH_NUMBER_RE = re.compile(r"\bbatch\s+number\b", re.I)
_PRODUCT_AFTER_NAMELY_RE = re.compile(
    r"\bnamely\s+the\s+(.+?)(?:,|\s+in order\b|\s+so\b|\.|$)",
    re.I,
)


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
        return [
            "Thank you for the quotation.",
            "",
            (
                f"I’ll send through the batch number for {product}. "
                "If the supplier confirms a separate production batch or reference, "
                "I’ll include it clearly so you can verify the quoted item."
            ),
        ]
    return None


def suggest_email_reply(
    analysis: dict[str, Any],
    *,
    operator_name: str = "",
) -> dict[str, Any]:
    """Build a suggested reply from an already-computed triage analysis.

    Takes the analyze_email_message() output directly rather than a raw
    message dict. This used to re-run analyze_email_message() itself on
    message["text"], but every caller passed the already-*truncated*
    280-char analysis["snippet"] as that text (the only copy of the body it
    had) -- a second, shorter pass over the same email that could reach a
    different, worse recommended_action (and a reply quoting a sentence
    fragment cut mid-word) than the first, full-text pass already sitting in
    `analysis`. Consuming that analysis directly removes the second pass
    entirely, so the reply always reflects the classification the operator
    actually sees on the signal.
    """

    subject = str(analysis.get("subject") or "").strip()
    sender = str(analysis.get("sender") or "").strip()
    action = str(analysis.get("recommended_action") or "monitor_email").strip()
    detail = str(analysis.get("recommended_detail") or "").strip()
    action_requests = [str(item).strip() for item in (analysis.get("action_requests") or []) if str(item).strip()]
    risks = [str(item).strip() for item in (analysis.get("risks") or []) if str(item).strip()]
    due_markers = [str(item).strip() for item in (analysis.get("due_markers") or []) if str(item).strip()]

    def _clip(text: str, limit: int = 220) -> str:
        # Sentence-splitting has no signal for "a quoted forwarded thread
        # starts here" -- a request sitting right before one can otherwise
        # pull the entire quoted chain in as one "sentence".
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject or '(no subject)'}"
    greeting_name = _sender_greeting(sender)

    body_lines = [f"Hi {greeting_name},", ""]
    ask_reply = _reply_for_current_ask(text=" ".join(action_requests), subject=subject)
    if ask_reply:
        body_lines.extend(ask_reply)
    elif action == "reply_or_investigate":
        body_lines.append(
            "Thanks for flagging this — I am looking into it now and will come back with a concrete update."
        )
        if risks:
            body_lines.append("")
            body_lines.append(f"I noted the risk around: {_clip(risks[0])}")
    elif action == "capture_follow_up":
        if action_requests:
            # Answer what was actually asked instead of a bare "noted" --
            # up to two asks read naturally; a third would start to feel
            # like a dump of internal extraction rather than a reply.
            if len(action_requests) == 1:
                body_lines.append(f"Thanks for the note — on it: {_clip(action_requests[0])}")
            else:
                body_lines.append("Thanks for the note. Working through what you asked:")
                for request in action_requests[:2]:
                    body_lines.append(f"- {_clip(request)}")
        else:
            body_lines.append("Thanks for the note. I’ll work through this and come back with the requested update.")
    elif action == "record_commitment":
        body_lines.append(
            "Thanks — confirming I have recorded the commitment and will track it through to completion."
        )
    else:
        body_lines.append("Thanks for the update — I have reviewed the thread and will keep an eye on it.")

    if due_markers:
        body_lines.append("")
        body_lines.append(f"Timing noted: {', '.join(due_markers[:3])}.")

    body_lines.extend(["", *_signature_lines(operator_name)])
    body = "\n".join(body_lines).strip() + "\n"

    return {
        "reply_subject": reply_subject,
        "reply_body": body,
        "to": sender,
        "recommended_action": action,
        "recommended_detail": detail,
        "priority": int(analysis.get("priority") or 0),
        "risk_level": str(analysis.get("risk_level") or "low"),
        "analysis": analysis,
    }
