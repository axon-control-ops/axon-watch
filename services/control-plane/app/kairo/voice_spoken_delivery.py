"""Spoken-reply shortening for VAXON voice turns (TTS vs UI transcript)."""

from __future__ import annotations

import re


def short_spoken_summary(
    reply: str,
    *,
    max_chars: int = 280,
    max_sentences: int = 2,
) -> str:
    trimmed = re.sub(r"\s+", " ", reply.strip())
    if not trimmed:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", trimmed)
    summary = ""
    sentence_count = 0
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        next_summary = f"{summary} {candidate}".strip()
        if len(next_summary) > max_chars:
            break
        summary = next_summary
        sentence_count += 1
        if sentence_count >= max_sentences:
            break
    if summary:
        return summary
    if len(trimmed) <= max_chars:
        return trimmed
    shortened = trimmed[: max_chars - 1].rstrip(" ,;:")
    return f"{shortened}…"


def spoken_delivery_summary(reply: str, *, deep: bool) -> str:
    """TTS may be shorter than the UI reply; deep/status reports keep more detail."""
    if deep:
        return short_spoken_summary(reply, max_chars=900, max_sentences=6)
    return short_spoken_summary(reply, max_chars=280, max_sentences=2)
