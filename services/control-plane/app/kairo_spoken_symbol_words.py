"""Strip literal spoken symbol/punctuation names before TTS."""

from __future__ import annotations

import re

# Longer phrases first so "smiley face" wins over a bare "face" rule (we do not strip "face").
_LITERAL_SYMBOL_WORD_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsmiley\s+face\b", re.IGNORECASE),
    re.compile(r"\bgrinning\s+face\b", re.IGNORECASE),
    re.compile(r"\bwinking\s+face\b", re.IGNORECASE),
    re.compile(r"\bemoji\b", re.IGNORECASE),
    re.compile(r"\bback\s*slash(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bforward\s+slash(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bhash\s+sign(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bcolon(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bslash(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bunderscore(?:s)?\b", re.IGNORECASE),
    re.compile(r"\basterisk(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bhashtag(?:s)?\b", re.IGNORECASE),
)


def strip_literal_symbol_words(text: str) -> str:
    """Remove spoken punctuation/symbol names the model may emit literally."""
    out = str(text or "")
    if not out:
        return ""
    for pattern in _LITERAL_SYMBOL_WORD_RES:
        out = pattern.sub(" ", out)
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r",\s*,+", ",", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,")
    return out.strip()
