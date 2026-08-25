"""Diagnose a Lead-role shift failure and decide the recovery card, instead of
escalating every failure unconditionally.

Root cause this replaces: lead_team_checkin.collect_failed_shift_findings()
used to hardcode every Lead-role failure as escalate_only=True with zero
diagnosis (`if role == "lead": owner_role, escalate_only = "watcher", True`),
and the frontend (lead-checkin-card.ts's optionsFor()) turned any non-empty
finding into a 4-option "how should the Lead handle this?" menu regardless of
whether a real business choice existed. This module is the "inspect, classify,
decide" step the autonomous recovery ladder needs before either of those.

The autonomous recovery ladder (subset implemented here — the parts that are
genuinely safe to automate without new destructive capability):
  1. Inspect the failure detail and the live delivery/runtime configuration.
  2. Classify the failure.
  3. Attempt the safest reversible fix (retry a transient interruption).
  4. Route to the correct specialist when the failure is outside Lead's role.
  5. Ask only when a genuine operator gate is hit (missing config/credential/
     billing, or safe attempts are exhausted) — and even then, only render a
     choices menu (decision_required) when a real fork exists; otherwise
     "blocked" (a single missing requirement, no invented menu).
"""

from __future__ import annotations

from app.workspace_agents.failure_detail import (
    is_billing_block_failure,
    is_billing_failure,
    is_runtime_auth_failure,
    is_shift_continuation_failure,
    is_usage_limit_failure,
    normalize_operator_failure_detail,
)
from app.workspace_agents.recovery_decision import EvidenceRef, RecoveryDecision

# Same boundary ask_autopilot.py already uses to decide what Auto mode must
# never choose on its own. Reused here rather than duplicated so "what counts
# as operator-only" stays one decision, defined once.
from app.workspace_agents.ask_autopilot import _UNSAFE_MARKERS

# A Lead check-in finding is retried automatically at most this many times
# before the ladder gives up and surfaces a "failed" card instead of looping.
# Mirrors the spirit of task_store's attempt_budget for leased tasks, but
# scoped to this dedupe key via the caller-supplied attempt count (kept pure
# here; lead_team_checkin.py is responsible for counting prior receipts).
MAX_AUTO_RECOVERY_ATTEMPTS = 3


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _workspace_delivery_configured(workspace_id: str) -> bool:
    """Ground truth, not string-matching the failure text.

    The failure message ("workspace delivery is not configured for X") could
    change wording; the live policy is the actual thing being diagnosed.
    """
    from app.workspace_delivery.config import get_workspace_delivery_policy

    try:
        policy = get_workspace_delivery_policy(workspace_id)
    except Exception:  # noqa: BLE001 — a diagnosis probe must never crash the check-in
        return True  # unknown: don't claim a config problem we couldn't verify
    return policy is not None and policy.enabled


def diagnose_lead_failure(
    *,
    workspace_id: str,
    run_id: str,
    detail: str,
    prior_attempts: int = 0,
) -> RecoveryDecision:
    """Classify a Lead-role shift failure into a RecoveryDecision.

    Pure with respect to global state except for one read-only config lookup
    (_workspace_delivery_configured) — no writes, no retries performed here.
    The caller (lead_team_checkin.py) executes whatever the decision's
    automatic_next_action calls for and persists attempt history.
    """
    normalized = normalize_operator_failure_detail(detail)
    evidence = (EvidenceRef(label="Failed run", ref=run_id),) if run_id else ()

    # 1. Transient interruption (restart, operator stop, OOM-kill) — always
    #    safe to retry, this is exactly what task continuation already means
    #    elsewhere in the codebase (isShiftContinuationFailure on the frontend).
    if is_shift_continuation_failure(normalized):
        if prior_attempts >= MAX_AUTO_RECOVERY_ATTEMPTS:
            return RecoveryDecision(
                card_type="failed",
                summary=f"The shift kept getting interrupted after {prior_attempts} retries.",
                classification="shift_continuation_exhausted",
                operator_action_required=True,
                recommended_action=(
                    "Check whether the host is under memory pressure or being restarted "
                    "repeatedly, then retry manually."
                ),
                automatic_next_action=None,
                actions_attempted=(f"Resumed the shift {prior_attempts} time(s)",),
                evidence=evidence,
                confidence=0.6,
                retry_eligible=False,
                recovery_eligible=False,
                escalation_reason="Safe retries were exhausted without the shift completing.",
            )
        return RecoveryDecision(
            card_type="working",
            summary="The last shift was interrupted (restart or stop), not a real failure.",
            classification="shift_continuation",
            operator_action_required=False,
            recommended_action="Resume the shift.",
            automatic_next_action="Resume the shift from where it left off.",
            actions_attempted=(f"Detected interruption (attempt {prior_attempts + 1})",),
            evidence=evidence,
            confidence=0.85,
            retry_eligible=True,
            recovery_eligible=True,
        )

    # 2. Missing credential / usage limit / billing hold — a genuine operator
    #    gate (spec: "A required credential, connection or permission is
    #    missing"), but a SINGLE specific missing thing, not a menu of
    #    business choices. Blocked, not decision_required.
    if is_usage_limit_failure(normalized):
        return RecoveryDecision(
            card_type="blocked",
            summary="The runtime is out of usage and cannot dispatch more shifts.",
            classification="usage_limit",
            operator_action_required=True,
            recommended_action="Increase the runtime's usage limit, or switch the workspace to a runtime with headroom.",
            automatic_next_action=None,
            actions_attempted=("Checked the runtime usage signal",),
            evidence=evidence,
            confidence=0.9,
            retry_eligible=False,
            recovery_eligible=False,
            escalation_reason="A usage-limit block requires an operator/billing action; the Lead has no authority to raise it.",
        )
    if is_billing_failure(normalized) or is_billing_block_failure(normalized):
        return RecoveryDecision(
            card_type="blocked",
            summary="A billing hold is blocking this workspace's runtime.",
            classification="billing_block",
            operator_action_required=True,
            recommended_action="Clear the outstanding invoice, then retry.",
            automatic_next_action=None,
            actions_attempted=("Checked the billing/invoice signal",),
            evidence=evidence,
            confidence=0.9,
            retry_eligible=False,
            recovery_eligible=False,
            escalation_reason="Billing is an account-level action; the Lead cannot pay an invoice.",
        )
    if is_runtime_auth_failure(normalized):
        return RecoveryDecision(
            card_type="blocked",
            summary="The agent runtime isn't signed in.",
            classification="runtime_auth",
            operator_action_required=True,
            recommended_action="Sign the runtime CLI back in (or unlock the vault), then retry.",
            automatic_next_action=None,
            actions_attempted=("Checked runtime auth status",),
            evidence=evidence,
            confidence=0.9,
            retry_eligible=False,
            recovery_eligible=False,
            escalation_reason="Runtime credentials are host-level; the Lead has no scope to re-authenticate them.",
        )

    # 3. Missing workspace-delivery configuration — diagnosed against the
    #    live policy, not the error string. This is the exact failure from
    #    the reported example. One missing requirement, no competing
    #    business choices: Blocked, never decision_required.
    if not _workspace_delivery_configured(workspace_id):
        return RecoveryDecision(
            card_type="blocked",
            summary=f"Workspace delivery isn't configured for {workspace_id}.",
            classification="missing_workspace_delivery_config",
            operator_action_required=True,
            recommended_action=(
                f"Enable a workspace delivery policy for {workspace_id} "
                "(base branch, push policy, and repo) before the Lead can publish changes."
            ),
            automatic_next_action=None,
            actions_attempted=(
                "Inspected the failed run",
                "Checked the live workspace delivery policy — confirmed disabled or absent",
            ),
            evidence=evidence,
            confidence=0.95,
            retry_eligible=False,
            recovery_eligible=False,
            escalation_reason=(
                "Workspace delivery policy is a host/operator-level configuration the Lead "
                "has no scope to create — retrying would fail identically."
            ),
        )

    # 4. Any other failure whose text touches operator-only territory
    #    (destructive/production/credentials/customer data/...) stays a
    #    genuine gate rather than being auto-routed.
    if _contains_any(normalized, _UNSAFE_MARKERS):
        return RecoveryDecision(
            card_type="blocked",
            summary="This failure touches a operator-sensitive action and was not auto-handled.",
            classification="operator_sensitive",
            operator_action_required=True,
            recommended_action="Review the failure detail and decide the next step.",
            automatic_next_action=None,
            actions_attempted=("Inspected the failure detail",),
            evidence=evidence,
            confidence=0.5,
            retry_eligible=False,
            recovery_eligible=False,
            escalation_reason=f"Detail mentions operator-sensitive territory: {normalized[:200]}",
        )

    # 5. Everything else: not a business decision, not an operator-only
    #    signal — route it to a specialist for investigation the same way a
    #    non-Lead failure would be routed. No ask.
    return RecoveryDecision(
        card_type="working",
        summary="Diagnosing this failure and routing it to a specialist.",
        classification="unclassified_routable",
        operator_action_required=False,
        recommended_action="Route to a specialist for investigation.",
        automatic_next_action="Create a scoped follow-up task for the owning specialist.",
        actions_attempted=("Inspected the failure detail", "Checked known failure signatures — none matched"),
        evidence=evidence,
        confidence=0.4,
        retry_eligible=False,
        recovery_eligible=True,
    )


__all__ = ["diagnose_lead_failure", "MAX_AUTO_RECOVERY_ATTEMPTS"]
