"""HTTP routes for the safe-improvement vertical slice."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.safe_improvement import proposal_service, store

router = APIRouter(prefix="/api/safe-improvement", tags=["safe-improvement"])


class TraceBody(BaseModel):
    workspace_id: str
    source_kind: str = "run"
    source_ref: str
    summary: str
    receipt_refs: list[str] = Field(default_factory=list)
    redacted_payload: dict[str, Any] = Field(default_factory=dict)


class CaseBody(BaseModel):
    name: str
    metric: str
    threshold: float
    comparator: str = "lte"
    baseline_value: float | None = None
    case_id: str | None = None


class ProposalBody(BaseModel):
    workspace_id: str
    trace_id: str
    case_id: str
    title: str
    effect_kind: str = "merge"
    target_ref: str = "main"


class EvaluateBody(BaseModel):
    candidate_value: float


class RequestApprovalBody(BaseModel):
    target_ref: str = "main"
    expires_hours: int = 24


class ApproveBody(BaseModel):
    effect_fingerprint: str
    approved_by: str = "operator"


@router.post("/traces")
def create_trace(body: TraceBody) -> dict[str, Any]:
    trace = proposal_service.capture_trace(
        workspace_id=body.workspace_id,
        source_kind=body.source_kind,
        source_ref=body.source_ref,
        summary=body.summary,
        receipt_refs=body.receipt_refs,
        redacted_payload=body.redacted_payload,
    )
    return trace.to_dict()


@router.post("/cases")
def create_case(body: CaseBody) -> dict[str, Any]:
    case = proposal_service.upsert_evaluation_case(
        name=body.name,
        metric=body.metric,
        threshold=body.threshold,
        comparator=body.comparator,
        baseline_value=body.baseline_value,
        case_id=body.case_id,
    )
    return case.to_dict()


@router.post("/proposals")
def create_proposal(body: ProposalBody) -> dict[str, Any]:
    try:
        proposal = proposal_service.create_proposal(
            workspace_id=body.workspace_id,
            trace_id=body.trace_id,
            case_id=body.case_id,
            title=body.title,
            effect_kind=body.effect_kind,
            target_ref=body.target_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.get("/proposals")
def list_proposals(limit: int = 20) -> dict[str, Any]:
    return {"proposals": store.list_proposals(limit=limit)}


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str) -> dict[str, Any]:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return proposal.to_dict()


@router.post("/proposals/{proposal_id}/evaluate")
def evaluate_proposal(proposal_id: str, body: EvaluateBody) -> dict[str, Any]:
    try:
        proposal = proposal_service.evaluate_proposal(
            proposal_id,
            candidate_value=body.candidate_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/proposals/{proposal_id}/request-approval")
def request_approval(proposal_id: str, body: RequestApprovalBody) -> dict[str, Any]:
    try:
        proposal = proposal_service.request_exact_approval(
            proposal_id,
            target_ref=body.target_ref,
            expires_hours=body.expires_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str, body: ApproveBody) -> dict[str, Any]:
    try:
        proposal = proposal_service.approve_exact_effect(
            proposal_id,
            effect_fingerprint=body.effect_fingerprint,
            approved_by=body.approved_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/proposals/{proposal_id}/execute")
def execute_proposal(proposal_id: str) -> dict[str, Any]:
    try:
        proposal = proposal_service.execute_approved_proposal(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/proposals/{proposal_id}/rollback")
def rollback_proposal(proposal_id: str) -> dict[str, Any]:
    try:
        proposal = proposal_service.rollback_proposal(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return proposal.to_dict()
