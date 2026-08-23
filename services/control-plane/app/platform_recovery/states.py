"""Recovery projection states. These do not replace run phases."""

from __future__ import annotations

# Operator-facing recovery buckets (Recovery Center columns).
RECOVERY_BUCKETS = (
    "ACTIVE",
    "STALE",
    "ORPHANED",
    "RESUMABLE",
    "RETRYABLE",
    "FAILED",
    "BLOCKED",
    "HUMAN_REVIEW",
)

# Diagnostic outcomes after a stale candidate is inspected.
DIAGNOSTIC_OUTCOMES = (
    "RUNNING",
    "RECOVERY_REQUIRED",
    "RESUMABLE",
    "RETRYABLE",
    "FAILED",
    "HUMAN_REVIEW",
)

FAILURE_CLASSES = (
    "PROCESS_LOST",
    "HEARTBEAT_EXPIRED",
    "LEASE_EXPIRED",
    "PROVIDER_TIMEOUT",
    "PROVIDER_RATE_LIMIT",
    "PROVIDER_AUTH_FAILURE",
    "NETWORK_FAILURE",
    "WORKTREE_FAILURE",
    "DEPENDENCY_FAILURE",
    "TEST_FAILURE",
    "VERIFIER_FAILURE",
    "CONFIGURATION_FAILURE",
    "RESOURCE_EXHAUSTION",
    "UNKNOWN",
)

AUTHORITY = (
    "AUTOMATIC",
    "HUMAN_APPROVAL",
    "ADMIN_APPROVAL",
    "FORBIDDEN",
)

RECOVERY_ACTIONS = (
    "RECONCILE",
    "RESUME",
    "RETRY",
    "CANCEL",
    "ARCHIVE",
    "DISCARD_TEMPORARY_ARTIFACTS",
    "ACKNOWLEDGE",
    "INSPECT",
    "WAIT",
    "FIX_CREDENTIALS",
    "HUMAN_REVIEW",
)

# Evidence lifecycle — never collapse these.
EVIDENCE_STATES = (
    "PLANNED",
    "DISPATCHED",
    "OBSERVED",
    "VERIFIED",
    "APPROVED",
)

AGENT_STATUSES = (
    "READY",
    "PLANNING",
    "DISPATCHING",
    "RUNNING",
    "WAITING",
    "STUCK",
    "STALE",
    "RECOVERING",
    "VERIFYING",
    "BLOCKED",
    "FAILED",
    "OFFLINE",
    "DISABLED",
)

CIRCUIT_STATES = ("CLOSED", "OPEN", "HALF_OPEN")

AUTONOMY_LEVELS = {
    0: "DIAGNOSTIC_ONLY",
    1: "AUTO_RECONCILE",
    2: "AUTO_RETRY_LOW_RISK",
    3: "AUTO_RESUME_CHECKPOINTED",
    4: "AUTO_REPAIR_VERIFIED_LOW_RISK",
    5: "SUPERVISED_MULTI_STEP",
}


def normalize_bucket(value: str | None) -> str:
    raw = str(value or "").strip().upper()
    return raw if raw in RECOVERY_BUCKETS else "HUMAN_REVIEW"


def normalize_failure_class(value: str | None) -> str:
    raw = str(value or "").strip().upper()
    return raw if raw in FAILURE_CLASSES else "UNKNOWN"
