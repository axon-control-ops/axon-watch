"""Shared Lead text helpers (public) for takeover / VAXON / spoken builders."""

from __future__ import annotations

import re

_CONFIDENCE_LINE_RE = re.compile(r"^\s*confidence\s*:?\s*\d+\s*/\s*10\s*$", re.I)
_CONFIDENCE_INLINE_RE = re.compile(r"\bConfidence:?\s*\d+\s*/\s*10\b", re.I)


def strip_thinking(text: str | None) -> str:
    """Drop :::thinking / :::tool fences; keep the last substantive segment."""
    raw = str(text or "")
    if ":::thinking" not in raw.lower() and ":::tool" not in raw.lower():
        return raw
    parts = raw.split(":::")
    for part in reversed(parts):
        cleaned = part.strip()
        lowered = cleaned.lower()
        if cleaned and not lowered.startswith("thinking") and not lowered.startswith("tool"):
            return cleaned
    return raw


def truncate_text(text: str | None, *, max_len: int = 280) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if len(cleaned) <= max_len:
        return cleaned
    if max_len <= 1:
        return "…"[:max_len]
    candidate = cleaned[: max_len - 1].rstrip()
    # Publish a complete final word, never fragments such as "C…" or "implem…".
    boundary = candidate.rfind(" ")
    if boundary > 0:
        candidate = candidate[:boundary].rstrip(" ,;:-–—")
    return f"{candidate}…"


def strip_confidence_lines(text: str | None) -> str:
    """Remove Confidence: N/10 crumbs so TTS stays natural."""
    body = strip_thinking(text)
    if not body:
        return ""
    kept: list[str] = []
    for line in body.splitlines():
        if _CONFIDENCE_LINE_RE.match(line.strip()):
            continue
        cleaned = _CONFIDENCE_INLINE_RE.sub("", line).strip()
        if cleaned:
            kept.append(cleaned)
    return " ".join(kept).strip()


def lead_summary_from_reply(reply_text: str | None) -> str:
    """One short Lead-facing summary line — never a full specialist dump."""
    body = strip_thinking(reply_text)
    if not body:
        return ""
    for line in body.splitlines():
        cleaned = line.strip().lstrip("-*• ").strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered.startswith(("what changed", "verified", "blockers", "confidence:", "lead:")):
            continue
        if _CONFIDENCE_LINE_RE.match(cleaned):
            continue
        cleaned = _CONFIDENCE_INLINE_RE.sub("", cleaned).strip()
        if cleaned:
            return truncate_text(cleaned, max_len=280)
    return truncate_text(strip_confidence_lines(body), max_len=280)


__all__ = [
    "lead_summary_from_reply",
    "strip_confidence_lines",
    "strip_thinking",
    "truncate_text",
]
