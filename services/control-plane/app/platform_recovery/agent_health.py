"""Evidence-based agent health. Not a cosmetic badge."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store


def score_agent_health(*, workspace_id: str | None = None, role: str | None = None) -> dict[str, Any]:
    runs = [
        record
        for record in run_store.list_runs()
        if (not workspace_id or str(record.get("workspace_id") or "") == workspace_id)
        and (not role or str(record.get("employee_role") or "") == role)
    ]
    completed = sum(1 for record in runs if str(record.get("phase")) == "completed")
    failed = sum(1 for record in runs if str(record.get("phase")) == "failed")
    cancelled = sum(1 for record in runs if str(record.get("phase")) == "cancelled")
    stale = sum(
        1
        for record in runs
        if not is_terminal_phase(str(record.get("phase") or ""))
        and str(record.get("phase")) in {"paused", "executing"}
    )
    total = max(1, completed + failed + cancelled)
    success_rate = completed / total
    score = int(round(100 * success_rate - 8 * stale - 4 * failed))
    score = max(0, min(100, score))
    factors = {
        "successful_runs": completed,
        "recent_failures": failed,
        "stale_or_paused": stale,
        "cancelled": cancelled,
        "success_rate": round(success_rate, 3),
    }
    return {
        "score": score,
        "label": _label(score),
        "factors": factors,
        "explanation": (
            f"Score {score}/100 from {completed} verified completions out of {total} "
            f"terminal runs, minus penalties for {failed} failures and {stale} stale/paused runs."
        ),
    }


def _label(score: int) -> str:
    if score >= 80:
        return "healthy"
    if score >= 50:
        return "degraded"
    return "unhealthy"
