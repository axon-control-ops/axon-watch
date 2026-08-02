"""Full-AUTO CEO — auto-approve investigable Needs-you cards (monitor + failed shifts)."""

from __future__ import annotations

import logging
from typing import Any

from app.workspace_agents.autonomous_attention_dedupe import (
    collapse_pending_decisions,
    soft_dedupe_key,
)
from app.workspace_agents.autonomous_attention_policy import (
    AutonomyPolicyDecision,
    text_looks_dangerous,
)
from app.workspace_agents.failure_detail import is_shift_continuation_failure

logger = logging.getLogger(__name__)

DEFAULT_CEO_APPROVE_MAX = 5

# Never auto-approve these — still need a human.
_CEO_NEVER_AUTO_KINDS = frozenset(
    {
        "secrets_blocker",
        "dangerous_action",
        "production_risk",
        "pending_approval",
    }
)

# Monitor / shift failures VAXON owns under Full autonomy (investigate + fix).
_CEO_INVESTIGABLE_KINDS = frozenset(
    {
        "critical_signal",
        "operator_blocker",
        "failed_shift",
        "warning_signal",
        "high_signal",
        "monitor_alert",
    }
)


def receipt_is_ceo_investigable(receipt: dict[str, Any]) -> bool:
    """True when Full-AUTO VAXON may Approve without parking on the operator."""
    kind = str(receipt.get("kind") or "").strip().lower()
    if not kind or kind in _CEO_NEVER_AUTO_KINDS:
        return False
    if kind not in _CEO_INVESTIGABLE_KINDS:
        return False
    title = str(receipt.get("title") or "")
    detail = str(receipt.get("detail") or "")
    dedupe = str(receipt.get("dedupe_key") or "")
    if text_looks_dangerous(title, detail, kind, dedupe):
        return False
    # Restart / operator stop / SIGTERM — escalate only; no repair attend under Full AUTO.
    if is_shift_continuation_failure(detail):
        return False
    # operator_blocker only when it is a failed-shift / monitor-shaped card.
    if kind == "operator_blocker":
        soft = soft_dedupe_key(dedupe)
        if not (
            soft.startswith("failed_shift:")
            or soft.startswith("signal:")
            or "last shift failed" in title.lower()
        ):
            return False
    return True


def finding_is_ceo_auto_dispatch(
    *,
    kind: str,
    title: str = "",
    detail: str = "",
    dedupe_key: str = "",
) -> bool:
    """True when enqueue should dispatch instead of escalate under Full AUTO."""
    return receipt_is_ceo_investigable(
        {
            "kind": kind,
            "title": title,
            "detail": detail,
            "dedupe_key": dedupe_key,
        }
    )


def ceo_dispatch_policy_if_full_auto(
    policy: AutonomyPolicyDecision,
    *,
    kind: str,
    title: str = "",
    detail: str = "",
    dedupe_key: str = "",
) -> AutonomyPolicyDecision | None:
    """Under Full AUTO, rewrite investigable escalations into auto-safe dispatch."""
    if policy.decision == "dispatch" and not policy.ask_operator:
        return None
    from app.persistence import operator_presence_settings_store

    mode = str(
        operator_presence_settings_store.load_settings().get("autonomy_mode") or ""
    ).strip().lower()
    if mode != "full":
        return None
    if not finding_is_ceo_auto_dispatch(
        kind=kind, title=title, detail=detail, dedupe_key=dedupe_key
    ):
        return None
    return AutonomyPolicyDecision(
        tier="auto_safe",
        decision="dispatch",
        risk="normal",
        reason=f"ceo_full_auto:{policy.reason}",
        ask_operator=False,
    )


def ceo_auto_approve_pending(
    *,
    max_decisions: int = DEFAULT_CEO_APPROVE_MAX,
    require_full_autonomy: bool = True,
) -> dict[str, Any]:
    """Approve investigable pending Needs-you cards so workers can lease attend tasks."""
    from app.host_context.models import utc_now_iso
    from app.persistence import autonomous_attention_store, operator_presence_settings_store
    from app.workspace_agents.autonomous_attention import resolve_autonomy_decision

    settings = operator_presence_settings_store.load_settings()
    mode = str(settings.get("autonomy_mode") or "").strip().lower()
    autonomy_full = mode == "full"
    if require_full_autonomy and not autonomy_full:
        return {
            "ok": False,
            "reason": "autonomy_not_full",
            "autonomy_full": False,
            "approved": [],
            "skipped": [],
            "remaining_pending": 0,
            "generated_at": utc_now_iso(),
        }

    pending = collapse_pending_decisions(
        autonomous_attention_store.list_pending_decisions(limit=500)
    )
    bound = max(1, min(20, int(max_decisions)))
    approved: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in pending:
        if len(approved) >= bound:
            break
        receipt_id = str(row.get("receipt_id") or "").strip()
        if not receipt_id:
            continue
        if not receipt_is_ceo_investigable(row):
            skipped.append(
                {
                    "receipt_id": receipt_id,
                    "reason": "not_investigable",
                    "kind": row.get("kind"),
                }
            )
            continue
        try:
            resolved = resolve_autonomy_decision(receipt_id, resolution="approved")
            approved.append(
                {
                    "receipt_id": receipt_id,
                    "kind": row.get("kind"),
                    "title": str(row.get("title") or "")[:96],
                    "workspace_id": row.get("workspace_id"),
                    "task_id": resolved.get("task_id"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("CEO auto-approve failed %s: %s", receipt_id, exc)
            skipped.append({"receipt_id": receipt_id, "reason": str(exc)})

    remaining = autonomous_attention_store.list_pending_decisions(limit=500)
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
                        "runId": "ceo-approve",
                        "hypothesisId": "E1",
                        "location": "ceo_pending_approve.py:ceo_auto_approve_pending",
                        "message": "ceo auto-approved pending needs-you",
                        "data": {
                            "autonomy_full": autonomy_full,
                            "approved": len(approved),
                            "skipped": len(skipped),
                            "remaining_pending": len(remaining),
                            "titles": [row.get("title") for row in approved[:5]],
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    return {
        "ok": True,
        "autonomy_full": autonomy_full,
        "approved": approved,
        "skipped": skipped,
        "remaining_pending": len(remaining),
        "spoken": (
            f"Approved {len(approved)} Needs-you card"
            f"{'' if len(approved) == 1 else 's'}"
            + (
                f"; {len(remaining)} still gated."
                if remaining
                else "."
            )
            if approved
            else "No investigable Needs-you cards to approve."
        ),
        "generated_at": utc_now_iso(),
    }


__all__ = [
    "ceo_auto_approve_pending",
    "ceo_dispatch_policy_if_full_auto",
    "finding_is_ceo_auto_dispatch",
    "receipt_is_ceo_investigable",
]
