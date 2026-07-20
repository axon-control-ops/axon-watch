"""Operator-readable failure detail normalization for roster and scheduler."""

from __future__ import annotations

import re

_LANE_B_FALLBACK_NORMALIZE_RE = re.compile(
    r"^Lane B (?:agent fallback reply generated|plan fallback failed)\s*\((.*)\)\s*$",
    re.IGNORECASE,
)
_DISPATCH_FAILURE_PREFIX = "continuous worker dispatch failed:"


def normalize_operator_failure_detail(detail: str | None) -> str:
    """Strip Lane B fallback wrappers so roster and retry prompts show root cause."""
    cleaned = " ".join(str(detail or "").split()).strip()
    if not cleaned:
        return cleaned
    match = _LANE_B_FALLBACK_NORMALIZE_RE.match(cleaned)
    if match:
        inner = " ".join(str(match.group(1) or "").split()).strip()
        primary = (inner.split(";")[0] if inner else inner).strip()
        return primary or inner
    if cleaned.lower().startswith(_DISPATCH_FAILURE_PREFIX):
        tail = cleaned[len(_DISPATCH_FAILURE_PREFIX) :].strip()
        return tail or cleaned
    return cleaned


def is_usage_limit_failure(detail: str | None) -> bool:
    """True when Cursor blocked the agent runtime for usage limits."""
    normalized = normalize_operator_failure_detail(detail)
    if not normalized:
        return False
    lowered = normalized.lower()
    return (
        "out of usage" in lowered
        or "increase limits" in lowered
        or "actionrequirederror" in lowered
    )
