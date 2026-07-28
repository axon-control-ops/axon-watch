"""Rewrite third-person self-narration into first person for employee agents."""

from __future__ import annotations

import re

from app.workspace_agents.employee_persona_prompt import EMPLOYEE_PERSONA_MARKER

_YOU_ARE_NAME_RE = re.compile(
    r"You are\s+([A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+)?)\.",
)


def employee_name_from_persona_block(context_block: str | None) -> str | None:
    """Pull the roster name from an Employee persona appendix, when present."""
    text = str(context_block or "")
    if EMPLOYEE_PERSONA_MARKER not in text:
        return None
    match = _YOU_ARE_NAME_RE.search(text)
    if not match:
        return None
    name = str(match.group(1) or "").strip()
    return name or None


def rewrite_employee_third_person_to_first(text: str, employee_name: str | None) -> str:
    """Convert '{Name} is planning…' into 'I am planning…' for the active employee.

    Models often narrate the persona in third person even when the prompt forbids it.
    This is a bounded post-process for known self-reference patterns only.
    """
    cleaned = str(text or "")
    name = " ".join(str(employee_name or "").strip().split())
    if not cleaned or not name:
        return cleaned

    escaped = re.escape(name)

    # Leading / mid-sentence: "Lindi is planning" → "I am planning"
    cleaned = re.sub(
        rf"(?i)\b{escaped}\s+is\b",
        "I am",
        cleaned,
    )
    cleaned = re.sub(
        rf"(?i)\b{escaped}\s+was\b",
        "I was",
        cleaned,
    )
    cleaned = re.sub(
        rf"(?i)\b{escaped}\s+will\b",
        "I will",
        cleaned,
    )
    cleaned = re.sub(
        rf"(?i)\b{escaped}\s+has\b",
        "I have",
        cleaned,
    )
    cleaned = re.sub(
        rf"(?i)\b{escaped}\s+does\b",
        "I do",
        cleaned,
    )
    # Possessive self-reference: "Lindi's shift" → "my shift"
    cleaned = re.sub(
        rf"(?i)\b{escaped}'s\b",
        "my",
        cleaned,
    )
    cleaned = re.sub(
        rf"(?i)\b{escaped}\u2019s\b",
        "my",
        cleaned,
    )
    # "As Lindi, …" / "As Lindi …"
    cleaned = re.sub(
        rf"(?i)\bas\s+{escaped}\b[,]?\s*",
        "",
        cleaned,
    )
    # Collapse double spaces after removals.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() if cleaned.strip() else str(text or "")


__all__ = [
    "employee_name_from_persona_block",
    "rewrite_employee_third_person_to_first",
]
