"""Deterministic reply drafts for triaged operator email."""

from __future__ import annotations

from typing import Any

from app.signals.email_triage import analyze_email_message


def suggest_email_reply(
    message: dict[str, Any],
    *,
    operator_name: str = "Axon operator",
) -> dict[str, Any]:
    """Build a suggested reply from triage analysis (no LLM required)."""

    analysis = analyze_email_message(message)
    subject = str(analysis.get("subject") or message.get("subject") or "").strip()
    sender = str(analysis.get("sender") or message.get("from") or "").strip()
    snippet = str(analysis.get("snippet") or message.get("snippet") or message.get("text") or "").strip()
    action = str(analysis.get("recommended_action") or "monitor_email").strip()
    detail = str(analysis.get("recommended_detail") or "").strip()
    action_requests = [str(item).strip() for item in (analysis.get("action_requests") or []) if str(item).strip()]
    risks = [str(item).strip() for item in (analysis.get("risks") or []) if str(item).strip()]
    due_markers = [str(item).strip() for item in (analysis.get("due_markers") or []) if str(item).strip()]

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject or '(no subject)'}"
    greeting_name = sender.split("<", 1)[0].strip().strip('"') or "there"
    if "," in greeting_name:
        greeting_name = greeting_name.split(",", 1)[0].strip()
    greeting_name = greeting_name.split()[0] if greeting_name else "there"

    body_lines = [f"Hi {greeting_name},", ""]
    if action == "reply_or_investigate":
        body_lines.append(
            "Thanks for flagging this — I am looking into it now and will come back with a concrete update."
        )
        if risks:
            body_lines.append("")
            body_lines.append(f"I noted the risk around: {risks[0]}")
    elif action == "capture_follow_up":
        body_lines.append("Thanks for the note. I have captured the follow-up and will action it.")
        if action_requests:
            body_lines.append("")
            body_lines.append(f"Working from: {action_requests[0]}")
    elif action == "record_commitment":
        body_lines.append(
            "Thanks — confirming I have recorded the commitment and will track it through to completion."
        )
    else:
        body_lines.append("Thanks for the update — I have reviewed the thread and will keep an eye on it.")

    if due_markers:
        body_lines.append("")
        body_lines.append(f"Timing noted: {', '.join(due_markers[:3])}.")

    if snippet and action in {"reply_or_investigate", "capture_follow_up"}:
        body_lines.append("")
        body_lines.append(f"Regarding: {snippet[:180]}")

    body_lines.extend(["", f"Best regards,", operator_name])
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
