"""Bounded smalltalk helpers for KAIRO conversation."""

from __future__ import annotations

import re

_SELF_RE = re.compile(
    r"\b(who are you|what are you|tell me about yourself|introduce yourself|what do you do)\b",
    re.IGNORECASE,
)


def self_intro_candidates(content: str) -> list[str]:
    if not _SELF_RE.search(content.strip()):
        return []
    return [
        "I'm VAXON, sir — your JARVIS for Axon-X. I watch the workspace, the runtime, and the control plane, then answer with the shortest useful truth.",
        "VAXON here. Mission control with manners: live workspace state, clear options, no fiction.",
        "I'm VAXON. Grounded in the repo, the runtime, and the control plane — ask for status, structure, or the next sensible move.",
    ]

