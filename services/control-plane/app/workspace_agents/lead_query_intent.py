"""Detect read-only domain questions that Lead should delegate."""

from __future__ import annotations

import re


_SPECIALIST_QUERY_RE = re.compile(
    r"(?:\bhow\s+many\b|\bcount\b|\blook\s*up\b|\bquery\b|\bfetch\b|\bfind\s+out\b)"
    r"[\s\S]{0,160}\b(?:tenant|preschool|student|learner|child(?:ren)?|record|database|supabase)\b"
    r"|\b(?:tenant|preschool|student|learner|child(?:ren)?|record|database|supabase)\b"
    r"[\s\S]{0,160}(?:\bhow\s+many\b|\bcount\b|\blook\s*up\b|\bquery\b|\bfetch\b)",
    re.IGNORECASE,
)


def detect_specialist_query_intent(goal: str) -> bool:
    return bool(_SPECIALIST_QUERY_RE.search(goal or ""))


__all__ = ["detect_specialist_query_intent"]
