"""Safe improvement domain models (first vertical slice)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EffectKind = Literal["policy", "secret", "production", "merge"]
ProposalStatus = Literal[
    "draft",
    "evaluated",
    "awaiting_approval",
    "approved",
    "executing",
    "verified",
    "rolled_back",
    "failed",
    "rejected",
]


@dataclass(frozen=True)
class ImprovementTrace:
    trace_id: str
    created_at: str
    workspace_id: str
    source_kind: str
    source_ref: str
    summary: str
    receipt_refs: tuple[str, ...] = ()
    redacted_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    name: str
    metric: str
    threshold: float
    comparator: Literal["lte", "gte", "eq"] = "lte"
    baseline_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    metric: str
    baseline_value: float
    candidate_value: float
    threshold: float
    comparator: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EffectApproval:
    approval_id: str
    proposal_id: str
    effect_kind: EffectKind
    effect_fingerprint: str
    target_ref: str
    expires_at: str
    approved_at: str | None = None
    approved_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Proposal:
    proposal_id: str
    created_at: str
    workspace_id: str
    trace_id: str
    case_id: str
    status: ProposalStatus
    effect_kind: EffectKind
    title: str
    isolation_root: str | None = None
    baseline_marker: str | None = None
    candidate_marker: str | None = None
    verification: VerificationResult | None = None
    effect_fingerprint: str | None = None
    approval: EffectApproval | None = None
    receipts: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.verification is not None:
            payload["verification"] = self.verification.to_dict()
        if self.approval is not None:
            payload["approval"] = self.approval.to_dict()
        return payload
