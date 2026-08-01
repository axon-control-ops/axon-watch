"""Soft-key collapse for twin autonomy Needs-you cards (failed_shift by role)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def soft_dedupe_key(dedupe_key: str) -> str:
    """Collapse failed_shift:ws:role:run_id → failed_shift:ws:role."""
    key = str(dedupe_key or "").strip().lower()
    if not key:
        return ""
    parts = key.split(":")
    if parts and parts[0] == "failed_shift" and len(parts) >= 3:
        return f"failed_shift:{parts[1]}:{parts[2]}"
    return key


def receipt_soft_key(receipt: dict[str, Any]) -> str:
    soft = soft_dedupe_key(str(receipt.get("dedupe_key") or ""))
    if soft:
        return soft
    title = str(receipt.get("title") or "").strip().lower()
    workspace = str(receipt.get("workspace_id") or "").strip().lower()
    kind = str(receipt.get("kind") or "").strip().lower()
    if title:
        return f"{kind}:{workspace}:{title}"
    return str(receipt.get("receipt_id") or "").strip().lower()


def collapse_pending_decisions(pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep newest receipt per soft key so VAXON never stacks twin Needs-you cards."""
    seen: set[str] = set()
    collapsed: list[dict[str, Any]] = []
    for row in pending:
        soft = receipt_soft_key(row)
        if soft in seen:
            continue
        seen.add(soft)
        collapsed.append(row)
    return collapsed


def reject_duplicate_pending(*, primary_id: str, soft_key: str) -> int:
    """Close stacked twins after the operator acts on one card."""
    from app.persistence import autonomous_attention_store

    cleared = 0
    if not soft_key:
        return cleared
    for row in autonomous_attention_store.list_pending_decisions(limit=500):
        twin_id = str(row.get("receipt_id") or "").strip()
        if not twin_id or twin_id == primary_id:
            continue
        if receipt_soft_key(row) != soft_key:
            continue
        try:
            autonomous_attention_store.begin_decision_resolution(twin_id)
            autonomous_attention_store.complete_decision_resolution(
                twin_id,
                resolution="rejected",
            )
            cleared += 1
        except Exception:
            logger.warning(
                "could not auto-clear duplicate autonomy decision %s", twin_id
            )
            try:
                autonomous_attention_store.release_decision_resolution(twin_id)
            except Exception:
                pass
    return cleared


__all__ = [
    "collapse_pending_decisions",
    "receipt_soft_key",
    "reject_duplicate_pending",
    "soft_dedupe_key",
]
