"""Shared conversational voice for Lead/specialist agent replies (Imani/Cole/Ash-style).

Every mode/role today reinvents its own tone guidance (or has none at all —
see worker_prompt.py::build_continuous_worker_prompt). This module is the
single shared "how to talk" clause for Lead and specialist agent-to-operator
chat, matching the same idempotent marker+append pattern as
critical_review_clause.py.
"""

from __future__ import annotations

# Stable marker for idempotent append (do not rephrase this substring lightly).
AGENT_VOICE_STYLE_MARKER = "Voice (how you talk to Sir King):"

AGENT_VOICE_STYLE_CLAUSE = (
    f"{AGENT_VOICE_STYLE_MARKER} talk the way a sharp, direct engineer would in a live "
    "conversation — plain language, short sentences, no corporate status-report jargon. "
    "Lead with the one sentence that actually matters (what changed, what's true now, "
    "what you need) instead of narrating your process end to end. Do not restate the "
    "request back before answering it. Do not pad routine replies with template "
    "scaffolding — headers, forced sections, or a sign-off ritual — unless the content "
    "genuinely needs a table or list to stay readable. Skip filler like \"I hope this "
    "helps\" or restating your own name/role. Say what you did and what's next, plainly, "
    "and stop."
)


def _has_agent_voice_style(text: str) -> bool:
    return AGENT_VOICE_STYLE_MARKER in (text or "")


def append_agent_voice_style(prompt: str) -> str:
    """Append the shared conversational voice clause unless already present."""
    text = (prompt or "").rstrip()
    if _has_agent_voice_style(text):
        return text or AGENT_VOICE_STYLE_CLAUSE
    if not text:
        return AGENT_VOICE_STYLE_CLAUSE
    return f"{text} {AGENT_VOICE_STYLE_CLAUSE}"


__all__ = [
    "AGENT_VOICE_STYLE_CLAUSE",
    "AGENT_VOICE_STYLE_MARKER",
    "append_agent_voice_style",
]
