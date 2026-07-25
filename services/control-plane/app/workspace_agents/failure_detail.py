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


_RUNTIME_AUTH_MARKERS = (
    "not signed in",
    "cursor agent login",
    "codex login",
    "unlock /vault",
    "vault locked",
    "cursor rejected cursor_api_key",
    "authentication failed",
    "authentication required",
    "api_key_invalid",
)


def is_runtime_auth_failure(detail: str | None) -> bool:
    """True when the agent runtime could not authenticate (CLI login or vault keys)."""
    normalized = normalize_operator_failure_detail(detail)
    if not normalized:
        return False
    lowered = normalized.lower()
    return any(marker in lowered for marker in _RUNTIME_AUTH_MARKERS)


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
