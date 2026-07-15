"""Proposal lifecycle for the safe-improvement vertical slice."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.safe_improvement import isolated_executor, store
from app.safe_improvement.models import (
    EffectApproval,
    EvaluationCase,
    ImprovementTrace,
    Proposal,
)
from app.safe_improvement.policy import (
    classify_effect,
    effect_fingerprint,
    fingerprints_match,
)
from app.safe_improvement.verifier import evaluate_against_threshold


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_receipt(proposal: Proposal, receipt: dict[str, Any]) -> None:
    proposal.receipts.append(receipt)


def capture_trace(
    *,
    workspace_id: str,
    source_kind: str,
    source_ref: str,
    summary: str,
    receipt_refs: list[str] | None = None,
    redacted_payload: dict[str, Any] | None = None,
) -> ImprovementTrace:
    trace = ImprovementTrace(
        trace_id=f"trace_{uuid4().hex[:12]}",
        created_at=_now(),
        workspace_id=workspace_id.strip(),
        source_kind=source_kind.strip() or "run",
        source_ref=source_ref.strip(),
        summary=summary.strip(),
        receipt_refs=tuple(receipt_refs or ()),
        redacted_payload=dict(redacted_payload or {}),
    )
    store.save_trace(trace)
    return trace


def upsert_evaluation_case(
    *,
    name: str,
    metric: str,
    threshold: float,
    comparator: str = "lte",
    baseline_value: float | None = None,
    case_id: str | None = None,
) -> EvaluationCase:
    case = EvaluationCase(
        case_id=case_id or f"case_{uuid4().hex[:12]}",
        name=name.strip(),
        metric=metric.strip(),
        threshold=float(threshold),
        comparator=comparator,  # type: ignore[arg-type]
        baseline_value=baseline_value,
    )
    return store.save_case(case)


def create_proposal(
    *,
    workspace_id: str,
    trace_id: str,
    case_id: str,
    title: str,
    effect_kind: str = "merge",
    target_ref: str = "main",
) -> Proposal:
    trace = store.get_trace(trace_id)
    case = store.get_case(case_id)
    if trace is None:
        raise ValueError(f"unknown trace `{trace_id}`")
    if case is None:
        raise ValueError(f"unknown evaluation case `{case_id}`")
    kind = classify_effect(effect_kind)
    proposal_id = f"prop_{uuid4().hex[:12]}"
    fingerprint = effect_fingerprint(
        proposal_id=proposal_id,
        effect_kind=kind,
        target_ref=target_ref,
        payload={"title": title.strip(), "case_id": case_id, "trace_id": trace_id},
    )
    proposal = Proposal(
        proposal_id=proposal_id,
        created_at=_now(),
        workspace_id=workspace_id.strip(),
        trace_id=trace_id,
        case_id=case_id,
        status="draft",
        effect_kind=kind,
        title=title.strip(),
        effect_fingerprint=fingerprint,
    )
    store.save_proposal(proposal)
    return proposal


def evaluate_proposal(
    proposal_id: str,
    *,
    candidate_value: float,
) -> Proposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"unknown proposal `{proposal_id}`")
    case = store.get_case(proposal.case_id)
    if case is None:
        raise ValueError(f"unknown evaluation case `{proposal.case_id}`")

    root = isolated_executor.create_isolation_root(proposal_id=proposal.proposal_id)
    baseline_value = (
        float(case.baseline_value)
        if case.baseline_value is not None
        else isolated_executor.read_metric(root, case.metric)
    )
    baseline_marker = isolated_executor.read_marker(root)
    change_receipt = isolated_executor.apply_candidate_change(
        root,
        metric=case.metric,
        candidate_value=float(candidate_value),
    )
    candidate_metric = isolated_executor.read_metric(root, case.metric)
    verification = evaluate_against_threshold(
        case,
        baseline_value=baseline_value,
        candidate_value=candidate_metric,
    )
    proposal.isolation_root = str(root)
    proposal.baseline_marker = baseline_marker
    proposal.candidate_marker = isolated_executor.read_marker(root)
    proposal.verification = verification
    _append_receipt(proposal, change_receipt)
    _append_receipt(
        proposal,
        {
            "receipt_id": f"eval_{uuid4().hex[:12]}",
            "kind": "verification",
            **verification.to_dict(),
        },
    )
    if not verification.passed:
        proposal.status = "failed"
        proposal.error = verification.reason
    else:
        proposal.status = "evaluated"
        proposal.error = None
    store.save_proposal(proposal)
    return proposal


def request_exact_approval(
    proposal_id: str,
    *,
    target_ref: str,
    expires_hours: int = 24,
) -> Proposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"unknown proposal `{proposal_id}`")
    if proposal.status != "evaluated":
        raise ValueError("proposal must be evaluated before requesting approval")
    if proposal.verification is None or not proposal.verification.passed:
        raise ValueError("proposal verification must pass before approval")
    fingerprint = effect_fingerprint(
        proposal_id=proposal.proposal_id,
        effect_kind=proposal.effect_kind,
        target_ref=target_ref,
        payload={
            "title": proposal.title,
            "case_id": proposal.case_id,
            "trace_id": proposal.trace_id,
        },
    )
    proposal.effect_fingerprint = fingerprint
    expires_at = (
        datetime.now(UTC) + timedelta(hours=max(1, int(expires_hours)))
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    proposal.approval = EffectApproval(
        approval_id=f"eap_{uuid4().hex[:12]}",
        proposal_id=proposal.proposal_id,
        effect_kind=proposal.effect_kind,
        effect_fingerprint=fingerprint,
        target_ref=target_ref.strip(),
        expires_at=expires_at,
    )
    proposal.status = "awaiting_approval"
    store.save_proposal(proposal)
    return proposal


def approve_exact_effect(
    proposal_id: str,
    *,
    effect_fingerprint: str,
    approved_by: str = "operator",
) -> Proposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"unknown proposal `{proposal_id}`")
    if proposal.status != "awaiting_approval" or proposal.approval is None:
        raise ValueError("proposal is not awaiting exact-effect approval")
    if not fingerprints_match(proposal.approval.effect_fingerprint, effect_fingerprint):
        raise ValueError(
            "exact-effect fingerprint mismatch; re-request approval for the "
            "current proposal payload"
        )
    # Reject generic run approvals by requiring the SI approval id prefix.
    if not proposal.approval.approval_id.startswith("eap_"):
        raise ValueError("generic run approval cannot substitute for exact-effect approval")
    proposal.approval = EffectApproval(
        approval_id=proposal.approval.approval_id,
        proposal_id=proposal.approval.proposal_id,
        effect_kind=proposal.approval.effect_kind,
        effect_fingerprint=proposal.approval.effect_fingerprint,
        target_ref=proposal.approval.target_ref,
        expires_at=proposal.approval.expires_at,
        approved_at=_now(),
        approved_by=approved_by.strip() or "operator",
    )
    proposal.status = "approved"
    _append_receipt(
        proposal,
        {
            "receipt_id": f"apr_{uuid4().hex[:12]}",
            "kind": "exact_effect_approval",
            "effect_fingerprint": proposal.approval.effect_fingerprint,
            "approved_by": proposal.approval.approved_by,
        },
    )
    store.save_proposal(proposal)
    return proposal


def execute_approved_proposal(proposal_id: str) -> Proposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"unknown proposal `{proposal_id}`")
    if proposal.status != "approved" or proposal.approval is None:
        raise ValueError("proposal must be approved before execution")
    if not proposal.isolation_root:
        raise ValueError("proposal missing isolation root")
    proposal.status = "executing"
    store.save_proposal(proposal)
    root = Path(proposal.isolation_root)
    # Merge-slice: promote candidate marker as the verified effect in isolation only.
    (root / "PROMOTED").write_text(
        f"{proposal.candidate_marker or 'candidate'}\n",
        encoding="utf-8",
    )
    _append_receipt(
        proposal,
        {
            "receipt_id": f"exec_{uuid4().hex[:12]}",
            "kind": "isolated_merge_execute",
            "isolation_root": str(root),
            "promoted_marker": proposal.candidate_marker,
        },
    )
    proposal.status = "verified"
    store.save_proposal(proposal)
    return proposal


def rollback_proposal(proposal_id: str) -> Proposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"unknown proposal `{proposal_id}`")
    if not proposal.isolation_root or proposal.verification is None:
        raise ValueError("proposal has no isolation state to roll back")
    case = store.get_case(proposal.case_id)
    if case is None:
        raise ValueError(f"unknown evaluation case `{proposal.case_id}`")
    root = Path(proposal.isolation_root)
    receipt = isolated_executor.restore_baseline(
        root,
        baseline_marker=proposal.baseline_marker or "baseline",
        baseline_metric_value=proposal.verification.baseline_value,
        metric=case.metric,
    )
    promoted = root / "PROMOTED"
    if promoted.exists():
        promoted.unlink()
    _append_receipt(proposal, receipt)
    proposal.status = "rolled_back"
    proposal.candidate_marker = isolated_executor.read_marker(root)
    store.save_proposal(proposal)
    return proposal
