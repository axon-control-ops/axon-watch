"""Run receipts for research actions."""

from __future__ import annotations

import hashlib
import json


def research_receipt_summary(*, kind: str, target: str, provider: str, success: bool) -> str:
    status = "ok" if success else "failed"
    digest = hashlib.sha256(target.encode("utf-8")).hexdigest()[:12]
    return f"research {kind} {provider} {status} · target_hash={digest}"


def research_receipt_payload(
    *,
    kind: str,
    target: str,
    provider: str,
    success: bool,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "kind": kind,
        "target": target,
        "provider": provider,
        "success": success,
        "summary": research_receipt_summary(
            kind=kind,
            target=target,
            provider=provider,
            success=success,
        ),
        "payload": payload,
    }


def append_research_receipt(run_id: str, receipt: dict[str, object]) -> None:
    if not str(run_id or "").strip():
        return
    from app.runs.service import RunNotFoundError, append_run_execution_receipt

    try:
        append_run_execution_receipt(
            run_id,
            receipt_type="research",
            receipt_summary=str(receipt.get("summary") or "research action"),
            actor="research_service",
            success=bool(receipt.get("success")),
            intent=str(receipt.get("kind") or "research"),
        )
    except RunNotFoundError:
        return


def format_research_block(
    query: str,
    items: list[dict[str, str]],
    *,
    provider: str = "",
    kind: str = "",
) -> str:
    lines = [f"\n:::research {query.strip() or 'Research'}"]
    if kind.strip():
        lines.append(f"@kind {kind.strip()}")
    if provider.strip():
        lines.append(f"@provider {provider.strip()}")
    for item in items:
        title = str(item.get("title") or "Source").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        lines.append(f"- {title} | {url or 'about:blank'}")
        if snippet:
            lines.append(snippet)
    lines.append(":::\n")
    return "\n".join(lines)
