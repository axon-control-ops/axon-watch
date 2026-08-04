"""Executive-facing Lead brief helpers — think / decide / implement, not operator dumps."""

from __future__ import annotations

import re

from app.workspace_agents.lead_text import lead_summary_from_reply, truncate_text

_SHELL_CHORE_RE = re.compile(
    r"(?i)\b("
    r"npm\s+run|\.env\b|project\s+root|cd\s+|which\s+node|sqlite|"
    r"/home/\w+|open\s+my\s+lead\s+tab|run\s+from\s+project|"
    r"package\.json|scripts?/[\w./-]+"
    r")\b"
)
_OPERATOR_GATE_RE = re.compile(
    r"(?i)\b(decide|approve|confirm|your call|ship|release|merge to main|production)\b"
)
_JARGON_RE = re.compile(
    r"(?i)\b(specialist report|lead handoff|my read|dig is an input|"
    r"ask me what to do next|parent ask remains)\b"
)


def looks_like_shell_chore(text: str | None) -> bool:
    return bool(_SHELL_CHORE_RE.search(str(text or "")))


def needs_operator_gate(text: str | None) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    if looks_like_shell_chore(cleaned):
        return False
    return bool(_OPERATOR_GATE_RE.search(cleaned))


def plain_outcome(reply_text: str | None) -> str:
    """One plain-English outcome line; strip shell laundry and jargon labels."""
    from app.kairo.report_text import _scrub_operator_line

    summary = lead_summary_from_reply(reply_text)
    if not summary:
        return ""
    scrubbed = _scrub_operator_line(summary, max_len=180)
    scrubbed = _JARGON_RE.sub("", scrubbed)
    scrubbed = re.sub(r"\s+", " ", scrubbed).strip(" :-")
    lower = scrubbed.lower()
    # Script/path dumps are not executive outcomes — translate to operator English.
    if looks_like_shell_chore(scrubbed) or "scripts/" in lower or ".mjs" in lower:
        if "graduation" in lower or "pop" in lower or "parent" in lower:
            return (
                "Counts tooling is ready; verified parent response and proof-of-payment "
                "numbers are not confirmed yet."
            )
        return "Implementation work landed; verified result is not confirmed yet."
    return truncate_text(scrubbed, max_len=160)


def executive_next_step(
    *,
    lead_next: str | None,
    specialist_name: str,
    parent_ask: str | None,
    status: str,
) -> str:
    """Lead-owned next move. Shell chores stay with Lead; only real gates ask the operator."""
    name = (specialist_name or "the specialist").strip() or "the specialist"
    ask = truncate_text(parent_ask, max_len=100)
    next_raw = truncate_text(lead_next, max_len=160)

    if next_raw and looks_like_shell_chore(next_raw):
        return (
            "Next: I will finish the verification myself and bring you clear numbers — "
            "you do not need to run scripts or hunt the shell."
        )
    if next_raw and needs_operator_gate(next_raw):
        return (
            f"Decision for you: {next_raw}. "
            "My recommendation: approve that path unless you want a different order."
        )
    if next_raw:
        lowered = next_raw[0].lower() + next_raw[1:] if next_raw[0].isupper() else next_raw
        if not lowered.startswith(("i will", "i'll", "we will")):
            lowered = f"I will {lowered}"
        return f"Next: {lowered}."
    if status == "completed" and ask:
        return (
            f"Next: I will close the loop on “{ask}” using {name}'s result, "
            "then come back with a concrete recommendation — not an open question."
        )
    if status == "completed":
        return (
            f"Next: I will convert {name}'s result into the next assignment "
            "and only escalate if a real gate needs you."
        )
    return f"Next: I will triage {name}'s blockers and reassign if needed."


def compress_ask(parent_ask: str | None, *, max_len: int = 120) -> str:
    cleaned = truncate_text(parent_ask, max_len=max_len)
    if not cleaned:
        return ""
    # Drop duplicated "Can we" stacks into one readable clause when possible.
    cleaned = re.sub(r"(?i)\s*second\s*[-–—:]?\s*", " Also: ", cleaned)
    return cleaned


__all__ = [
    "compress_ask",
    "executive_next_step",
    "looks_like_shell_chore",
    "needs_operator_gate",
    "plain_outcome",
]
