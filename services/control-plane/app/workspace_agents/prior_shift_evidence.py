"""Hand a retry/review shift the artifacts of the work it is asked to review.

"Critically review your previous work" is unanswerable from a fresh worker
process: the prior shift ran as a different process, in a different isolation
checkout, with no shared transcript. Given only an error string, a well-behaved
agent refuses ("any review I produced would be invented, not verified") and a
badly-behaved one fabricates receipts. Both are system failures.

This resolves the concrete pointers — prior run id, delivery branch/commit/PR,
changed paths, and the gate reason — so the review has something real to open.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_REVIEW_INTENT_RE = re.compile(
    r"\b(review|re-?check|critique|rewrite|retry|re-?run|revisit|"
    r"previous work|prior work|last shift|your last)\b",
    re.IGNORECASE,
)
_MAX_PATHS = 12


def looks_like_review_or_retry(*parts: str) -> bool:
    """True when the shift is asked to act on work a previous shift produced."""
    return any(_REVIEW_INTENT_RE.search(str(part or "")) for part in parts)


def prior_failure_clause(*, workspace_id: str, role: str) -> str:
    """Surface the last terminal failure so a new shift can retry with context."""
    from app.workspace_agents.run_outcome import latest_role_run_outcome

    try:
        outcome = latest_role_run_outcome(workspace_id, role)
    except Exception:  # noqa: BLE001 - stale evidence must not block prompt assembly
        logger.debug("prior failure lookup failed for %s role=%s", workspace_id, role, exc_info=True)
        return ""
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return ""
    detail = str(outcome.get("detail") or "").strip() or "open run history for receipts"
    run_id = str(outcome.get("run_id") or "").strip()
    run_hint = f" (run {run_id})" if run_id else ""
    return (
        f" Prior shift failed{run_hint}: {detail}. "
        "Prefer fixing or clearing that failure before unrelated work. "
    )


def _delivery_refs(run_id: str) -> dict[str, str]:
    from app.workspace_delivery import store as delivery_store

    try:
        delivery = delivery_store.get_delivery_by_run(run_id)
    except Exception:  # noqa: BLE001 - evidence lookup must never fail a dispatch
        logger.exception("prior delivery lookup failed for %s", run_id)
        return {}
    if not isinstance(delivery, dict):
        return {}
    refs = delivery.get("refs") if isinstance(delivery.get("refs"), dict) else {}
    resolved = {
        "worker_branch": str(delivery.get("worker_branch") or refs.get("worker_branch") or ""),
        "commit_sha": str(delivery.get("commit_sha") or refs.get("commit_sha") or ""),
        "draft_pr_url": str(delivery.get("draft_pr_url") or refs.get("draft_pr_url") or ""),
        "stage": str(delivery.get("stage") or ""),
    }
    return {key: value for key, value in resolved.items() if value}


def _receipt_facts(run_id: str) -> tuple[list[str], str]:
    """Changed paths and the completion-gate reason from the prior run's receipts."""
    from app.persistence import run_store

    try:
        run = run_store.get_run(run_id)
        history = run_store.list_history(str((run or {}).get("history_ref") or ""))
    except Exception:  # noqa: BLE001
        logger.exception("prior receipt lookup failed for %s", run_id)
        return [], ""

    changed: list[str] = []
    gate_reason = ""
    for entry in history:
        receipt = entry.get("receipt") if isinstance(entry, dict) else None
        if not isinstance(receipt, dict):
            continue
        summary = str(receipt.get("summary") or "")
        if str(receipt.get("type") or "") != "completion_gate":
            continue
        reason = re.search(r"reason=([^·]+)", summary)
        if reason:
            gate_reason = reason.group(1).strip()
        paths = re.search(r"changed_files=([^·]+)", summary)
        if paths:
            listed = [item.strip() for item in paths.group(1).split(",") if item.strip()]
            if listed and listed != ["none"]:
                changed = listed[:_MAX_PATHS]
    return changed, gate_reason


def prior_shift_evidence_clause(*, workspace_id: str, role: str) -> str:
    """Name the reviewable artifacts of this role's most recent run."""
    from app.workspace_agents.run_outcome import latest_role_run_outcome

    outcome = latest_role_run_outcome(workspace_id, role)
    if not isinstance(outcome, dict):
        return ""
    run_id = str(outcome.get("run_id") or "").strip()
    if not run_id:
        return ""

    refs = _delivery_refs(run_id)
    changed, gate_reason = _receipt_facts(run_id)
    detail = str(outcome.get("detail") or "").strip()
    status = str(outcome.get("outcome") or "").strip() or "unknown"

    facts: list[str] = [f"prior run `{run_id}` ({status})"]
    if refs.get("draft_pr_url"):
        facts.append(f"draft PR {refs['draft_pr_url']}")
    if refs.get("worker_branch"):
        facts.append(f"branch `{refs['worker_branch']}`")
    if refs.get("commit_sha"):
        facts.append(f"commit `{refs['commit_sha'][:12]}`")
    if changed:
        facts.append("changed files " + ", ".join(f"`{path}`" for path in changed))
    if gate_reason:
        facts.append(f"gate reason: {gate_reason}")
    elif detail:
        facts.append(f"last error: {detail}")

    if len(facts) == 1 and not detail:
        # Only a run id and nothing to open — say so rather than implying more.
        return (
            f" PRIOR SHIFT EVIDENCE: the previous run is `{run_id}` ({status}) and left no "
            "delivery branch, commit, PR, or changed files. There is no artifact to review. "
            "Say that plainly and ask for a pointer instead of reconstructing what it did."
        )

    return (
        " PRIOR SHIFT EVIDENCE (resolved by the control plane — open these rather than "
        f"reconstructing from memory): {'; '.join(facts)}. "
        "A prior shift ran as a separate process with no shared transcript, so anything "
        "not listed here is not something you observed. Review the named artifacts, and if "
        "they do not cover what you were asked to review, say exactly what pointer is "
        "missing instead of inventing one."
    )


__all__ = [
    "looks_like_review_or_retry",
    "prior_failure_clause",
    "prior_shift_evidence_clause",
]
