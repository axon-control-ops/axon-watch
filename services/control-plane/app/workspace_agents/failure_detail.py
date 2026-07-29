"""Operator-readable failure detail normalization for roster and scheduler."""

from __future__ import annotations

import re

_LANE_B_FALLBACK_NORMALIZE_RE = re.compile(
    r"^Lane B (?:agent fallback reply generated|plan fallback failed)\s*\(([\s\S]*?)\s*\)?\s*$",
    re.IGNORECASE,
)
_DISPATCH_FAILURE_PREFIX = "continuous worker dispatch failed:"
_FAILURE_NOISE_RE = re.compile(r"^(?:running as unit|invocation id|scope)[:\s]", re.IGNORECASE)
_RUNTIME_AUTH_MARKERS = (
    "not signed in",
    "cursor agent login",
    "codex login",
    "claude auth login",
    "unlock /vault",
    "vault locked",
    "cursor rejected cursor_api_key",
    "authentication failed",
    "authentication required",
    "api_key_invalid",
    "auth probe timed out",
    "auth probe failed",
    "cursor auth probe",
    "codex auth probe",
    "claude auth probe",
)


def _pick_primary_failure_cause(inner: str) -> str:
    parts = [
        " ".join(part.split()).strip()
        for part in str(inner or "").split(";")
        if " ".join(part.split()).strip()
    ]
    parts = [part for part in parts if not _FAILURE_NOISE_RE.search(part)]
    if not parts:
        return " ".join(str(inner or "").split()).strip()

    def rank(part: str) -> int:
        lowered = part.lower()
        if "actionrequirederror" in lowered or "out of usage" in lowered or "increase limits" in lowered:
            return 0
        if any(marker in lowered for marker in _RUNTIME_AUTH_MARKERS):
            return 1
        if "failed on" in lowered:
            return 2
        if "unavailable" in lowered:
            return 4
        return 3

    return sorted(parts, key=rank)[0]


def normalize_operator_failure_detail(detail: str | None) -> str:
    """Strip Lane B fallback wrappers so roster and retry prompts show root cause."""
    cleaned = " ".join(str(detail or "").split()).strip()
    if not cleaned:
        return cleaned
    if cleaned.lower().startswith(_DISPATCH_FAILURE_PREFIX):
        tail = cleaned[len(_DISPATCH_FAILURE_PREFIX) :].strip()
        return _pick_primary_failure_cause(tail or cleaned)
    match = _LANE_B_FALLBACK_NORMALIZE_RE.match(cleaned)
    if match:
        return _pick_primary_failure_cause(match.group(1) or "")
    return _pick_primary_failure_cause(cleaned)


def is_usage_limit_failure(detail: str | None) -> bool:
    """True when Cursor blocked the agent runtime for usage limits.

    Bare ``ActionRequiredError`` is not enough — Cursor also uses that type for
    non-quota prompts. Require an explicit usage phrase.
    """
    hay = f"{detail or ''} {normalize_operator_failure_detail(detail)}".lower()
    matched = (
        "out of usage" in hay
        or "increase limits" in hay
        or "hit your usage" in hay
        or "usage limit" in hay
        or "you've hit your usage" in hay
        or "used 100% of your included" in hay
    )
    return matched


def is_runtime_auth_failure(detail: str | None) -> bool:
    """True when the agent runtime could not authenticate (CLI login, vault, or auth probe)."""
    hay = f"{detail or ''} {normalize_operator_failure_detail(detail)}".lower()
    return any(marker in hay for marker in _RUNTIME_AUTH_MARKERS)


_RESTART_INTERRUPT_MARKERS = (
    "run interrupted by control-plane restart",
    "run cancelled after control-plane restart",
    "run paused after control-plane restart",
    "continuous worker dispatch lost on control-plane restart",
    "continuous worker dispatch paused on control-plane restart",
    "continuous worker dispatch cancelled after control-plane restart",
)

_SESSION_INTERRUPT_RE = re.compile(
    r"exited with status (?:143|137|-?9\b)|\boom[- ]?kill|\bkilled by.*oom\b",
    re.IGNORECASE,
)


def is_restart_interrupted_failure(detail: str | None) -> bool:
    """True when a run ended only because the control-plane process restarted."""
    normalized = normalize_operator_failure_detail(detail)
    if not normalized:
        return False
    lowered = normalized.lower()
    return any(marker in lowered for marker in _RESTART_INTERRUPT_MARKERS)


def is_operator_stopped_failure(detail: str | None) -> bool:
    """True when the operator stopped the CLI before the shift could finish."""
    normalized = normalize_operator_failure_detail(detail)
    if not normalized:
        return False
    lowered = normalized.lower()
    return (
        "runtime execution stopped by operator" in lowered
        or "stopped by operator before the cli finished" in lowered
    )


def is_agent_session_interrupted_failure(detail: str | None) -> bool:
    """True when SIGTERM (143), SIGKILL/OOM (137 / -9), or OOM-kill stopped the agent."""
    normalized = normalize_operator_failure_detail(detail)
    if not normalized:
        return False
    return bool(_SESSION_INTERRUPT_RE.search(normalized))


def is_shift_continuation_failure(detail: str | None) -> bool:
    """Restart, operator stop, or SIGTERM — retry should continue rather than treat as a hard failure."""
    return (
        is_restart_interrupted_failure(detail)
        or is_operator_stopped_failure(detail)
        or is_agent_session_interrupted_failure(detail)
    )
