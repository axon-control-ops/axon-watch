"""Lightweight acceptance for direct, non-Task-Board Agent replies."""

from __future__ import annotations

from dataclasses import dataclass
import re


_STRUCTURED_BLOCK_RE = re.compile(
    r":::(?:terminal|edit|research|image|thinking|tool)\b[\s\S]*?:::",
    re.IGNORECASE,
)
_STRUCTURED_START_RE = re.compile(
    r":::(terminal|edit|research|image|thinking|tool)\b",
    re.IGNORECASE,
)
_ORPHAN_TOOL_MARKER_RE = re.compile(r"^:::tool\b[^\n]*(?:\n|$)", re.IGNORECASE | re.MULTILINE)
_MARKDOWN_NOISE_RE = re.compile(r"[`#>*_\-\s]+")


@dataclass(frozen=True)
class DirectReplyAcceptance:
    passed: bool
    summary: str


def narrative_outside_receipts(reply_text: str | None) -> str:
    """Return human-facing prose after removing machine receipt blocks."""
    raw = str(reply_text or "")
    without_closed = _STRUCTURED_BLOCK_RE.sub("\n", raw)
    without_closed = _ORPHAN_TOOL_MARKER_RE.sub("\n", without_closed)
    # An unclosed final receipt means the runtime stopped while still emitting
    # tool output. Ignore that tail rather than mistaking it for a final answer.
    unmatched = _STRUCTURED_START_RE.search(without_closed)
    if unmatched is not None:
        without_closed = without_closed[: unmatched.start()]
    return " ".join(without_closed.split()).strip()


def evaluate_direct_reply_acceptance(reply_text: str | None) -> DirectReplyAcceptance:
    """Require an operator-facing conclusion, not merely exit code zero."""
    raw = str(reply_text or "")
    starts = len(_STRUCTURED_START_RE.findall(raw))
    closed = len(_STRUCTURED_BLOCK_RE.findall(raw))
    if starts > closed:
        without_closed = _STRUCTURED_BLOCK_RE.sub("\n", raw)
        unmatched_kinds = [
            match.group(1).lower()
            for match in _STRUCTURED_START_RE.finditer(_ORPHAN_TOOL_MARKER_RE.sub("\n", without_closed))
        ]
        if any(kind != "tool" for kind in unmatched_kinds):
            return DirectReplyAcceptance(
                False,
                "Direct reply incomplete: runtime output ended inside an unclosed receipt block",
            )

    narrative = narrative_outside_receipts(raw)
    substantive = _MARKDOWN_NOISE_RE.sub("", narrative)
    if len(substantive) < 12:
        return DirectReplyAcceptance(
            False,
            "Direct reply incomplete: no human-facing conclusion followed the runtime receipts",
        )
    return DirectReplyAcceptance(True, "Direct reply includes a human-facing conclusion")


def enforce_direct_reply_acceptance(
    run_id: str,
    reply_text: str | None,
) -> tuple[bool, dict[str, object] | None]:
    """Record/fail lightweight acceptance for a non-Task-Board run."""
    from app.runs.service import (
        append_run_execution_receipt,
        fail_run,
        get_run,
    )

    current = get_run(run_id)
    if str(current.get("task_id") or "").strip():
        return True, None
    acceptance = evaluate_direct_reply_acceptance(reply_text)
    record = append_run_execution_receipt(
        run_id,
        receipt_type="direct_reply_acceptance",
        receipt_summary=acceptance.summary,
        actor="reply_verification",
        success=acceptance.passed,
        intent="lane_b_agent",
    )
    if acceptance.passed:
        return True, record
    return False, fail_run(
        run_id,
        receipt_summary=acceptance.summary,
        actor="reply_verification",
    )


__all__ = [
    "DirectReplyAcceptance",
    "enforce_direct_reply_acceptance",
    "evaluate_direct_reply_acceptance",
    "narrative_outside_receipts",
]
