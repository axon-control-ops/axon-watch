"""Cause-aware recovery policy. Never guess UNKNOWN into a retry."""

from __future__ import annotations

from dataclasses import dataclass

from app.platform_recovery.states import normalize_failure_class


@dataclass(frozen=True)
class RecoveryPolicy:
    failure_class: str
    action: str
    authority: str
    retry_safe: str  # "safe" | "unsafe" | "requires_approval"
    max_attempts: int
    backoff_seconds: tuple[int, ...]
    next_step: str
    auto_at_level: int


_POLICIES: dict[str, RecoveryPolicy] = {
    "PROCESS_LOST": RecoveryPolicy(
        "PROCESS_LOST", "RESUME", "AUTOMATIC", "safe", 2, (5, 15),
        "Worker process disappeared. Resume from the last checkpoint if it is valid.",
        3,
    ),
    "HEARTBEAT_EXPIRED": RecoveryPolicy(
        "HEARTBEAT_EXPIRED", "RECONCILE", "AUTOMATIC", "requires_approval", 1, (30,),
        "Heartbeat expired without meaningful progress. Inspect evidence before retry.",
        1,
    ),
    "LEASE_EXPIRED": RecoveryPolicy(
        "LEASE_EXPIRED", "RETRY", "AUTOMATIC", "safe", 2, (5, 20),
        "Lease expired. Re-lease the same task if no other owner exists.",
        2,
    ),
    "PROVIDER_TIMEOUT": RecoveryPolicy(
        "PROVIDER_TIMEOUT", "RETRY", "AUTOMATIC", "safe", 3, (5, 20, 60),
        "Provider timed out. Bounded backoff, then escalate.",
        2,
    ),
    "PROVIDER_RATE_LIMIT": RecoveryPolicy(
        "PROVIDER_RATE_LIMIT", "WAIT", "AUTOMATIC", "safe", 2, (60, 180),
        "Provider rate-limited. Wait, then one retry. Do not tight-loop.",
        2,
    ),
    "PROVIDER_AUTH_FAILURE": RecoveryPolicy(
        "PROVIDER_AUTH_FAILURE", "FIX_CREDENTIALS", "HUMAN_APPROVAL", "unsafe", 0, (),
        "Authentication failed. Do not retry. Fix vault/CLI credentials, then acknowledge.",
        99,
    ),
    "NETWORK_FAILURE": RecoveryPolicy(
        "NETWORK_FAILURE", "RETRY", "AUTOMATIC", "safe", 3, (5, 15, 45),
        "Network failure. Bounded backoff, then escalate.",
        2,
    ),
    "WORKTREE_FAILURE": RecoveryPolicy(
        "WORKTREE_FAILURE", "RECONCILE", "HUMAN_APPROVAL", "requires_approval", 1, (10,),
        "Worktree failed. Reconcile filesystem; never delete uncommitted work automatically.",
        1,
    ),
    "DEPENDENCY_FAILURE": RecoveryPolicy(
        "DEPENDENCY_FAILURE", "RECONCILE", "HUMAN_APPROVAL", "requires_approval", 1, (10,),
        "Dependency/lock mismatch. Repair declared versions, then verify.",
        4,
    ),
    "TEST_FAILURE": RecoveryPolicy(
        "TEST_FAILURE", "INSPECT", "HUMAN_APPROVAL", "requires_approval", 1, (),
        "This is a product test failure, not infrastructure. Preserve output and repair.",
        4,
    ),
    "VERIFIER_FAILURE": RecoveryPolicy(
        "VERIFIER_FAILURE", "INSPECT", "HUMAN_APPROVAL", "requires_approval", 1, (),
        "Verification did not accept the claim. Inspect the verifier receipt.",
        4,
    ),
    "CONFIGURATION_FAILURE": RecoveryPolicy(
        "CONFIGURATION_FAILURE", "HUMAN_REVIEW", "ADMIN_APPROVAL", "unsafe", 0, (),
        "Configuration is invalid. Do not retry until the named setting is fixed.",
        99,
    ),
    "RESOURCE_EXHAUSTION": RecoveryPolicy(
        "RESOURCE_EXHAUSTION", "WAIT", "AUTOMATIC", "requires_approval", 1, (60,),
        "Host resources are exhausted. Wait rather than dispatch another worker.",
        2,
    ),
    "UNKNOWN": RecoveryPolicy(
        "UNKNOWN", "HUMAN_REVIEW", "HUMAN_APPROVAL", "unsafe", 0, (),
        "Cause is unknown. Preserve evidence. Do not invent a retry.",
        99,
    ),
}


def policy_for(failure_class: str | None) -> RecoveryPolicy:
    return _POLICIES[normalize_failure_class(failure_class)]


def action_allowed_at_level(failure_class: str | None, autonomy_level: int) -> bool:
    policy = policy_for(failure_class)
    if policy.authority in {"FORBIDDEN"}:
        return False
    return int(autonomy_level) >= policy.auto_at_level
