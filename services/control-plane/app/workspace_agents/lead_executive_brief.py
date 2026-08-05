"""Plain executive Lead briefs: situation, verified outcome, Lead-owned next move."""

from __future__ import annotations

import re

from app.workspace_agents.lead_text import (
    lead_summary_from_reply,
    strip_thinking,
    truncate_text,
)

_SHELL_CHORE_RE = re.compile(
    r"(?i)(?:\bnpm\s+run\b|\.env\b|\bproject\s+root\b|\bcd\s+|"
    r"\bwhich\s+node\b|\bsqlite\b|/home/\w+|\bopen\s+my\s+lead\s+tab\b|"
    r"\brun\s+from\s+project\b|\bpackage\.json\b|\bscripts?/[\w./-]+)"
)
_OPERATOR_GATE_RE = re.compile(
    r"(?i)\b(decide|approve|confirm|your call|go-ahead|authorize|"
    r"ship|release|merge to main|production)\b"
)
_RUNTIME_PROTOCOL_RE = re.compile(
    r"(?i)\b(lane b agent could not start|thread\.started|thread[_ ]id|"
    r"run[_ ]id|continuous worker dispatch started)\b"
)
_INTERNAL_WORK_RE = re.compile(
    r"(?i)\b(failed_shift|dedupe|run_[a-z0-9]+|task-[a-z0-9]+|lead-plan-|"
    r"stale[- ]timeout|watcher cutoff|receipt|re-lease|lease|"
    r"accept clearance|handoff\*|idle against the \d+s)\b"
)
_JARGON_RE = re.compile(
    r"(?i)\b(specialist report|lead handoff|my read|dig is an input|"
    r"ask me what to do next|parent ask remains)\b"
)
_PARENT_POP_ASK_RE = re.compile(
    r"(?is)(?=.*\bparent)(?=.*\bgraduation)"
    r"(?=.*\b(?:pop|proof of payment|payment proofs?))"
)


def looks_like_shell_chore(text: str | None) -> bool:
    return bool(_SHELL_CHORE_RE.search(str(text or "")))


def needs_operator_gate(text: str | None) -> bool:
    cleaned = str(text or "").strip()
    if (
        not cleaned
        or looks_like_shell_chore(cleaned)
        or _INTERNAL_WORK_RE.search(cleaned)
    ):
        return False
    return bool(_OPERATOR_GATE_RE.search(cleaned))


def compress_ask(parent_ask: str | None, *, max_len: int = 150) -> str:
    raw = " ".join(str(parent_ask or "").split()).strip()
    if _RUNTIME_PROTOCOL_RE.search(raw):
        goal_match = re.search(r"(?i)\bgoal\s*[,;:]\s*(.+)$", raw)
        raw = goal_match.group(1).strip() if goal_match else raw
    raw = re.sub(r"(?i)^lead\s*[:,-]?\s*advance\s*", "", raw).strip(" \"'")
    raw = re.sub(r"(?i)\s*second\s*[-–—:]?\s*", " Also: ", raw)
    if _PARENT_POP_ASK_RE.search(raw):
        return (
            "Count parent graduation-card responses and payment proofs, then make "
            "chat-sent proof visible to parents and centre staff."
        )
    if looks_like_shell_chore(raw):
        return "Complete the requested result and verify that it is ready to use."
    raw = _JARGON_RE.sub("", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" :-")
    return truncate_text(raw, max_len=max_len)


def plain_outcome(reply_text: str | None) -> str:
    """Return one plain outcome without runtime protocol, shell work, or jargon."""
    from app.kairo.report_text import _scrub_operator_line

    body = strip_thinking(reply_text)
    body_lower = body.lower()
    if "stale-timeout" in body_lower or "stale timeout" in body_lower:
        return (
            "The previous background check ended after sitting idle too long. "
            "It did not identify a problem in the centre app."
        )
    if "ping timed out" in body_lower:
        return (
            "The previous attempt lost its connection before finishing. "
            "It did not identify a problem in the centre app."
        )
    summary = lead_summary_from_reply(reply_text)
    if not summary:
        return ""
    if _RUNTIME_PROTOCOL_RE.search(summary):
        return "The agent attempt failed before work started; no verified result landed."
    if _INTERNAL_WORK_RE.search(summary):
        return "Internal follow-up completed; the requested result still needs verification."
    if looks_like_shell_chore(summary):
        lower = summary.lower()
        if "graduation" in lower or "pop" in lower or "parent" in lower:
            return (
                "Counts tooling is ready; verified parent response and "
                "proof-of-payment numbers are not confirmed yet."
            )
        return "Implementation work landed; verification is not confirmed yet."
    scrubbed = _scrub_operator_line(summary, max_len=220)
    scrubbed = _JARGON_RE.sub("", scrubbed)
    scrubbed = re.sub(r"\s+", " ", scrubbed).strip(" :-")
    return truncate_text(scrubbed, max_len=180)


def executive_next_step(
    *,
    lead_next: str | None,
    specialist_name: str,
    parent_ask: str | None,
    status: str,
) -> str:
    name = (specialist_name or "the specialist").strip() or "the specialist"
    next_raw = truncate_text(lead_next, max_len=180)
    ask = compress_ask(parent_ask, max_len=140)
    if next_raw and (_INTERNAL_WORK_RE.search(next_raw) or _JARGON_RE.search(next_raw)):
        if _PARENT_POP_ASK_RE.search(ask):
            return (
                "I will continue the parent-response and payment-proof work, assign "
                "the remaining app changes, and return with verified counts and a "
                "ready-to-use result."
            )
        return (
            "I will clear the internal handoff, continue the original work, and "
            "report the verified outcome here."
        )
    if next_raw and looks_like_shell_chore(next_raw):
        return "I will finish the verification and bring you the result."
    if next_raw and needs_operator_gate(next_raw):
        return (
            "I will continue everything that is safe to progress while I hold the "
            "recommended decision for you below."
        )
    if next_raw:
        action = next_raw.rstrip(".")
        if action.lower().startswith(("i will ", "i'll ")):
            return f"{action}."
        action = action[0].lower() + action[1:] if action[0].isupper() else action
        return f"I will {action}."
    if status == "completed" and ask:
        return (
            f"I will close “{ask}” using {name}'s result and return with "
            "a concrete recommendation."
        )
    if status == "completed":
        return f"I will turn {name}'s result into the next assignment."
    return f"I will triage {name}'s blocker and reassign if needed."


def executive_operator_action(lead_next: str | None) -> str:
    next_raw = truncate_text(lead_next, max_len=180)
    if not next_raw or not needs_operator_gate(next_raw):
        return "Nothing right now. I will keep driving the work and report back here."
    return (
        f"Decision needed: {next_raw}. "
        "Recommendation: approve this path unless you want a different order."
    )


__all__ = [
    "compress_ask",
    "executive_next_step",
    "executive_operator_action",
    "looks_like_shell_chore",
    "needs_operator_gate",
    "plain_outcome",
]
