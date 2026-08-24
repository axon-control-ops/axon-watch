"""Next-best-action engine. Never leave the operator with 'something went wrong'."""

from __future__ import annotations

from typing import Any

from app.platform_recovery.policy import policy_for
from app.platform_recovery.states import normalize_bucket


def describe_next_action(
    *,
    bucket: str,
    failure_class: str = "UNKNOWN",
    checkpoint_valid: bool = False,
    lease_owner_alive: bool = False,
    retry_remaining: int = 0,
    idle_seconds: float | None = None,
) -> dict[str, Any]:
    policy = policy_for(failure_class)
    normalized = normalize_bucket(bucket)
    idle = "recently"
    if idle_seconds is not None:
        seconds = int(idle_seconds)
        if seconds >= 60:
            idle = f"{seconds // 60} minutes ago"
        else:
            idle = f"{seconds} seconds ago"

    if normalized == "ACTIVE":
        return {
            "action": "INSPECT",
            "authority": "AUTOMATIC",
            "summary": "The worker is still active. Watch the next stage transition.",
            "safe": True,
        }
    if normalized == "RESUMABLE" or (normalized == "STALE" and checkpoint_valid):
        return {
            "action": "RESUME",
            "authority": "AUTOMATIC" if checkpoint_valid else "HUMAN_APPROVAL",
            "summary": (
                f"The worker stopped responding {idle}. The last checkpoint is valid. "
                "Resume is safe because no irreversible action was recorded."
            ),
            "safe": bool(checkpoint_valid),
        }
    if normalized == "RETRYABLE" and retry_remaining > 0 and policy.retry_safe == "safe":
        return {
            "action": "RETRY",
            "authority": policy.authority,
            "summary": f"{policy.next_step} Retry budget remaining: {retry_remaining}.",
            "safe": True,
        }
    if normalized == "BLOCKED":
        return {
            "action": "HUMAN_REVIEW",
            "authority": "HUMAN_APPROVAL",
            "summary": "A human or external owner must act before work can continue.",
            "safe": False,
        }
    if failure_class == "PROVIDER_AUTH_FAILURE":
        return {
            "action": "FIX_CREDENTIALS",
            "authority": "HUMAN_APPROVAL",
            "summary": policy.next_step,
            "safe": False,
        }
    if lease_owner_alive and normalized == "STALE":
        return {
            "action": "RECONCILE",
            "authority": "AUTOMATIC",
            "summary": (
                f"A lease owner is still recorded but progress stopped {idle}. "
                "Reconcile the worker identity before retrying."
            ),
            "safe": True,
        }
    return {
        "action": policy.action,
        "authority": policy.authority,
        "summary": policy.next_step,
        "safe": policy.retry_safe == "safe",
    }
