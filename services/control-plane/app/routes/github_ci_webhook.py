"""GitHub Actions webhook → Gate 9 CI remediation ingest."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from app.ci_remediation.hmac_verify import verify_github_signature
from app.ci_remediation.ingest import ingest_workflow_run_event
from app.ci_remediation.report import mark_repair_outcome, spoken_report_line

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ci-remediation"])


@router.post("/api/webhooks/github/workflow-run")
async def github_workflow_run_webhook(request: Request) -> dict[str, object]:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(body=body, signature_header=signature):
        raise HTTPException(status_code=401, detail="invalid github webhook signature")

    event_name = (request.headers.get("X-GitHub-Event") or "").strip().lower()
    if event_name and event_name not in {"workflow_run", "ping"}:
        return {"ok": True, "ignored": True, "reason": f"event:{event_name}"}
    if event_name == "ping":
        return {"ok": True, "pong": True}

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid json: {exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be an object")

    result = ingest_workflow_run_event(payload)
    logger.info(
        "ci remediation ingest accepted=%s reason=%s dedupe=%s task=%s",
        result.accepted,
        result.reason,
        result.dedupe_key,
        result.task_id,
    )
    return {
        "ok": True,
        "accepted": result.accepted,
        "reason": result.reason,
        "dedupe_key": result.dedupe_key,
        "task_id": result.task_id,
        "run_id": result.run_id,
        "signal_id": result.signal_id,
        "duplicate": result.duplicate,
    }


@router.post("/api/ci-remediation/report-outcome")
def ci_remediation_report_outcome(body: dict[str, object]) -> dict[str, object]:
    """Worker/callback path to mark repair success or budget exhaustion."""
    dedupe = str(body.get("dedupe_key") or "").strip()
    workspace_id = str(body.get("workspace_id") or "workspace_axon_watch").strip()
    workflow_name = str(body.get("workflow_name") or "Axon-X Fast Gate").strip()
    head_branch = str(body.get("head_branch") or "").strip()
    success = bool(body.get("success"))
    detail = str(body.get("detail") or "").strip()
    html_url = str(body.get("html_url") or "").strip()
    draft_pr_url = str(body.get("draft_pr_url") or "").strip()
    if not dedupe:
        raise HTTPException(status_code=400, detail="dedupe_key is required")
    signal = mark_repair_outcome(
        dedupe_key=dedupe,
        workspace_id=workspace_id,
        workflow_name=workflow_name,
        head_branch=head_branch,
        success=success,
        detail=detail,
        html_url=html_url,
        draft_pr_url=draft_pr_url,
    )
    spoken = spoken_report_line(
        success=success,
        workflow_name=workflow_name,
        detail=detail or draft_pr_url or html_url,
    )
    return {
        "ok": True,
        "signal_id": signal.get("signal_id"),
        "spoken": spoken,
        "status": signal.get("status"),
    }
