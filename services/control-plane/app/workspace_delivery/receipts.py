"""Emit structured worker_delivery receipts onto run history."""

from __future__ import annotations

from typing import Any


def emit_delivery_receipt(
    run_id: str,
    *,
    stage: str,
    summary: str,
    success: bool = True,
    refs: dict[str, Any] | None = None,
    actor: str = "workspace_delivery",
) -> dict[str, Any]:
    from app.runs.service import append_run_execution_receipt

    cleaned_refs = {key: value for key, value in (refs or {}).items() if value not in (None, "")}
    ref_bits = []
    for key in ("worker_branch", "commit_sha", "draft_pr_url", "ci_run_url", "attempt", "blocker"):
        if key in cleaned_refs:
            ref_bits.append(f"{key}={cleaned_refs[key]}")
    body = summary.strip() or f"delivery stage={stage}"
    if ref_bits:
        body = f"{body} · {' · '.join(ref_bits)}"
    return append_run_execution_receipt(
        run_id,
        receipt_type="worker_delivery",
        receipt_summary=f"stage={stage} · {body}",
        actor=actor,
        success=success,
        intent="workspace_delivery",
    )


def delivery_refs_from_record(record: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    refs = dict(record.get("refs") or {})
    for key in (
        "worker_branch",
        "commit_sha",
        "draft_pr_url",
        "ci_run_url",
        "ci_conclusion",
        "attempt",
        "blocker",
    ):
        value = record.get(key)
        if value not in (None, "") and key not in refs:
            refs[key] = value
    return refs
