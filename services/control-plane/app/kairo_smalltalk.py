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
        "I'm VAXON, your voice-aware control point for Axon-X. I can answer from the workspace, runtime, and system state without wandering off into fiction.",
        "I'm VAXON. I keep one eye on the workspace and the other on live runtime state, then answer with the shortest useful truth I can give you.",
        "VAXON, sir — read-only in this lane, grounded in the repo, the runtime, and the control plane. Ask for status, structure, or the next sensible move.",
    ]

