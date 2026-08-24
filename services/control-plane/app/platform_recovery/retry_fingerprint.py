"""Bounded retry fingerprints. Same failure must not loop forever."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.platform_recovery.states import normalize_failure_class


@dataclass(frozen=True)
class RetryDecision:
    fingerprint: str
    attempt: int
    action: str  # retry | alternate | cooldown | HUMAN_REVIEW
    remaining: int


_ESCALATION = (
    (1, "retry"),
    (2, "alternate"),
    (3, "cooldown"),
)


def build_retry_fingerprint(
    *,
    failure_class: str,
    provider: str = "",
    task_id: str = "",
    command: str = "",
    error_signature: str = "",
    workspace_id: str = "",
    configuration_version: str = "",
) -> str:
    basis = "|".join(
        (
            normalize_failure_class(failure_class),
            str(provider or "").strip().lower(),
            str(task_id or "").strip(),
            str(command or "").strip()[:180],
            str(error_signature or "").strip()[:180],
            str(workspace_id or "").strip(),
            str(configuration_version or "").strip(),
        )
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"retry:{digest}"


def decide_retry(*, fingerprint: str, prior_attempts: int, max_attempts: int) -> RetryDecision:
    attempt = max(0, int(prior_attempts)) + 1
    if max_attempts <= 0 or attempt > max_attempts or attempt >= 4:
        return RetryDecision(fingerprint, attempt, "HUMAN_REVIEW", 0)
    for threshold, action in _ESCALATION:
        if attempt == threshold:
            remaining = max(0, max_attempts - attempt)
            return RetryDecision(fingerprint, attempt, action, remaining)
    return RetryDecision(fingerprint, attempt, "HUMAN_REVIEW", 0)
