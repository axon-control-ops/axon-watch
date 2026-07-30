"""Explicit assign/have-<Name> routing so Lead cannot keep specialist work."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.workspace_agents.teammate_route import TeammateRouteEmployee

_ASSIGN_VERBS = r"(?:assign|dispatch|hand[\s-]?off|give|send|route|pass)"
_HAVE_VERBS = r"(?:have|ask|tell|get)"


def _name_tokens(name: str) -> list[str]:
    full = " ".join(str(name or "").strip().split())
    if not full:
        return []
    first = full.split()[0]
    tokens = [full]
    if first and first.lower() != full.lower() and len(first) >= 2:
        tokens.append(first)
    return tokens


def match_named_assign_employee(
    prompt: str,
    roster: list[TeammateRouteEmployee] | None,
) -> TeammateRouteEmployee | None:
    """Return the roster teammate explicitly named in an assign/have prompt."""
    text = str(prompt or "").strip()
    if not text:
        return None
    employees = [row for row in (roster or []) if str(row.employee_id or "").strip() and str(row.name or "").strip()]
    if not employees:
        return None

    ranked = sorted(
        employees,
        key=lambda row: (-len(str(row.name).strip()), str(row.name).strip().lower()),
    )
    for employee in ranked:
        for token in _name_tokens(employee.name):
            escaped = re.escape(token)
            patterns = (
                re.compile(rf"\b{_ASSIGN_VERBS}\b[\s\S]{{0,48}}\b{escaped}\b", re.I),
                re.compile(rf"\b{_HAVE_VERBS}\b\s+{escaped}\b", re.I),
                re.compile(
                    rf"\b{escaped}\b[\s\S]{{0,24}}\b(?:should|needs?\s+to|will|can)\b",
                    re.I,
                ),
                re.compile(rf"@\s*{escaped}\b", re.I),
                re.compile(
                    rf"\b(?:to|for)\s+{escaped}\b[\s\S]{{0,24}}\b(?:task|job|work|this|it)\b",
                    re.I,
                ),
                re.compile(
                    rf"\b(?:task|job|work)\b[\s\S]{{0,24}}\b(?:to|for)\s+{escaped}\b",
                    re.I,
                ),
            )
            for pattern in patterns:
                if pattern.search(text):
                    return employee
    return None


def rewrite_named_assign_prompt(prompt: str, employee_name: str) -> str:
    """Strip assign framing so the specialist gets an actionable ask."""
    text = str(prompt or "").strip()
    if not text:
        return text
    name = " ".join(str(employee_name or "").strip().split())
    first = name.split()[0] if name else ""
    tokens = []
    for token in (name, first):
        if token and len(token) >= 2 and token not in tokens:
            tokens.append(token)
    cleaned = text
    for token in tokens:
        escaped = re.escape(token)
        cleaned = re.sub(rf"\b{_ASSIGN_VERBS}\b\s+{escaped}\b", " ", cleaned, flags=re.I)
        cleaned = re.sub(
            rf"\b{_ASSIGN_VERBS}\b\s+(?:this|the\s+task|it)\s+to\s+{escaped}\b",
            " ",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(rf"\b{_HAVE_VERBS}\b\s+{escaped}\b", " ", cleaned, flags=re.I)
        cleaned = re.sub(rf"@\s*{escaped}\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(
        r"\b(?:and\s+)?have\s+(?:him|her|them)\s+report\s+back\b",
        " ",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\breport\s+back\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\bthe\s+task\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" \t\r\n,.;:!?-")
    body = (
        cleaned
        if len(cleaned) >= 8
        else "Complete the assigned task from the Lead handoff and report back when done."
    )
    return (
        "You own this assignment from Lead. Complete it and report back when done.\n\n"
        f"Operator ask: {body}"
    )


def detect_named_assign_intent(prompt: str, roster: list[TeammateRouteEmployee] | None) -> bool:
    return match_named_assign_employee(prompt, roster) is not None


__all__ = [
    "detect_named_assign_intent",
    "match_named_assign_employee",
    "rewrite_named_assign_prompt",
]
