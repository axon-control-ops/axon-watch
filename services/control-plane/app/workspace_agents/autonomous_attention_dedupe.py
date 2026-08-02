"""Soft-key collapse for twin autonomy Needs-you cards (failed_shift by role)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
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


def receipt_task_still_blocking(task_id: str | None) -> bool:
    """Failed/cancelled attend tasks must not freeze CEO redrive forever."""
    cleaned = str(task_id or "").strip()
    if not cleaned:
        # Bare receipts (no task) must not lock the fleet; open tasks still dedupe.
        return False
    try:
        from app.persistence import task_store

        task = task_store.get_task(cleaned)
    except Exception:
        return True
    if task is None:
        return False
    status = str(task.get("status") or "").strip().lower()
    if status in {"failed", "cancelled"}:
        return False
    return True


def has_recent_dedupe_key(
    dedupe_key: str,
    *,
    cooldown_seconds: int = 900,
) -> bool:
    """True when a soft-key twin is still pending/resolving/cooling down."""
    from app.persistence import autonomous_attention_store

    key = str(dedupe_key or "").strip()
    if not key:
        return False
    soft = soft_dedupe_key(key)
    pending = autonomous_attention_store.list_pending_decisions(limit=500)
    if any(soft_dedupe_key(str(row.get("dedupe_key") or "")) == soft for row in pending):
        return True
    resolving = autonomous_attention_store.list_receipts(limit=500, status="resolving")
    if any(soft_dedupe_key(str(row.get("dedupe_key") or "")) == soft for row in resolving):
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=max(1, int(cooldown_seconds))
    )
    skip_failed = 0
    for row in autonomous_attention_store.list_receipts(limit=500):
        if soft_dedupe_key(str(row.get("dedupe_key") or "")) != soft:
            continue
        raw = str(row.get("resolved_at") or row.get("created_at") or "").replace(
            "Z", "+00:00"
        )
        try:
            created = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created.astimezone(timezone.utc) < cutoff:
            continue
        # Allow Full-AUTO redrive when the prior attend attempt already failed.
        if not receipt_task_still_blocking(row.get("task_id")):
            skip_failed += 1
            continue
        # #region agent log
        try:
            import json
            import time

            with open(
                "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-db8bb4.log",
                "a",
                encoding="utf-8",
            ) as _dbg:
                _dbg.write(
                    json.dumps(
                        {
                            "sessionId": "db8bb4",
                            "runId": "ceo-engage",
                            "hypothesisId": "D1",
                            "location": "autonomous_attention_dedupe.py:has_recent_dedupe_key",
                            "message": "dedupe blocks redrive",
                            "data": {
                                "soft": soft,
                                "task_id": row.get("task_id"),
                                "skip_failed": skip_failed,
                            },
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        return True
    # #region agent log
    if skip_failed:
        try:
            import json
            import time

            with open(
                "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-db8bb4.log",
                "a",
                encoding="utf-8",
            ) as _dbg:
                _dbg.write(
                    json.dumps(
                        {
                            "sessionId": "db8bb4",
                            "runId": "ceo-engage",
                            "hypothesisId": "D1",
                            "location": "autonomous_attention_dedupe.py:has_recent_dedupe_key",
                            "message": "dedupe allows redrive after failed attend",
                            "data": {"soft": soft, "skip_failed": skip_failed},
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
    # #endregion
    return False


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
    "has_recent_dedupe_key",
    "receipt_soft_key",
    "receipt_task_still_blocking",
    "reject_duplicate_pending",
    "soft_dedupe_key",
]
