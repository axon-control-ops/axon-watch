"""Plain executive Lead briefs: situation, verified outcome, Lead-owned next move."""

from __future__ import annotations

import re

from app.workspace_agents.lead_text import lead_summary_from_reply, truncate_text

_SHELL_CHORE_RE = re.compile(
    r"(?i)\b(npm\s+run|\.env\b|project\s+root|cd\s+|which\s+node|"
    r"/home/\w+|package\.json|scripts?/[\w./-]+)\b"
)
_OPERATOR_GATE_RE = re.compile(
    r"(?i)\b(decide|approve|confirm|ship|release|merge to main|production)\b"
)
_RUNTIME_PROTOCOL_RE = re.compile(
    r"(?i)\b(lane b agent could not start|thread\.started|thread[_ ]id|"
    r"run[_ ]id|continuous worker dispatch started)\b"
)


def compress_ask(parent_ask: str | None, *, max_len: int = 150) -> str:
    raw = " ".join(str(parent_ask or "").split()).strip()
    if _RUNTIME_PROTOCOL_RE.search(raw):
        goal_match = re.search(r"(?i)\bgoal\s*[,;:]\s*(.+)$", raw)
        raw = goal_match.group(1).strip() if goal_match else raw
    raw = re.sub(r"(?i)^lead\s*[:,-]?\s*advance\s*", "", raw).strip(" \"'")
    raw = re.sub(r"(?i)\s*second\s*[-–—:]?\s*", " Also: ", raw)
    return truncate_text(raw, max_len=max_len)


def plain_outcome(reply_text: str | None) -> str:
    summary = lead_summary_from_reply(reply_text)
    if not summary:
        return ""
    if _RUNTIME_PROTOCOL_RE.search(summary):
        return "The agent attempt failed before work started; no verified result landed."
    if _SHELL_CHORE_RE.search(summary):
        lower = summary.lower()
        if "graduation" in lower or "pop" in lower or "parent" in lower:
            return (
                "Counts tooling is ready; verified parent response and "
                "proof-of-payment numbers are not confirmed yet."
            )
        return "Implementation work landed; verification is not confirmed yet."
    return truncate_text(summary, max_len=180)


def executive_next_step(
    *,
    lead_next: str | None,
    specialist_name: str,
    parent_ask: str | None,
    status: str,
) -> str:
    name = (specialist_name or "the specialist").strip() or "the specialist"
    next_raw = truncate_text(lead_next, max_len=180)
    ask = truncate_text(parent_ask, max_len=120)
    if next_raw and _SHELL_CHORE_RE.search(next_raw):
        return (
            "Next: I will finish the verification and bring you the result; "
            "you do not need to run scripts or hunt the shell."
        )
    if next_raw and _OPERATOR_GATE_RE.search(next_raw):
        return (
            f"Decision for you: {next_raw}. "
            "My recommendation is to approve that path unless you want a different order."
        )
    if next_raw:
        action = next_raw[0].lower() + next_raw[1:] if next_raw[0].isupper() else next_raw
        return f"Next: I will {action}."
    if status == "completed" and ask:
        return (
            f"Next: I will close “{ask}” using {name}'s result and return with "
            "a concrete recommendation."
        )
    if status == "completed":
        return f"Next: I will turn {name}'s result into the next assignment."
    return f"Next: I will triage {name}'s blocker and reassign if needed."


__all__ = ["compress_ask", "executive_next_step", "plain_outcome"]
