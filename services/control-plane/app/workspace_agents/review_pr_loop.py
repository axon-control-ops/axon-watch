"""Gate 7/8 — independent review + draft PR / CI repair loop (bounded)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DEFAULT_MAX_REPAIR_ATTEMPTS = 3
DEFAULT_MAX_ELAPSED_SECONDS = 45 * 60
DEFAULT_MAX_TOKEN_BUDGET = 250_000


@dataclass
class ReviewFinding:
    severity: str
    summary: str
    path: str = ""
    actionable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewVerdict:
    passed: bool
    reviewer: str
    findings: list[ReviewFinding] = field(default_factory=list)
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reviewer": self.reviewer,
            "blocking": self.blocking,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class RepairLoopState:
    attempts: int = 0
    elapsed_seconds: int = 0
    tokens_used: int = 0
    max_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS
    max_elapsed_seconds: int = DEFAULT_MAX_ELAPSED_SECONDS
    max_token_budget: int = DEFAULT_MAX_TOKEN_BUDGET
    abandoned: bool = False
    abandon_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assert_independent_reviewer(implementer: str, reviewer: str) -> None:
    left = str(implementer or "").strip().lower()
    right = str(reviewer or "").strip().lower()
    if not right:
        raise ValueError("reviewer identity required")
    if left and left == right:
        raise ValueError("reviewer must be independent from the implementer")


def review_task_diff(
    *,
    implementer: str,
    reviewer: str,
    task_contract: dict[str, Any],
    diff_summary: str,
    verifier_receipts: list[dict[str, Any]],
) -> ReviewVerdict:
    """Defect-first review over task contract + diff + verifier receipts."""
    assert_independent_reviewer(implementer, reviewer)
    findings: list[ReviewFinding] = []

    if not task_contract.get("acceptance_criteria"):
        findings.append(
            ReviewFinding(
                severity="high",
                summary="task contract missing acceptance_criteria",
                actionable=True,
            )
        )
    if not verifier_receipts:
        findings.append(
            ReviewFinding(
                severity="critical",
                summary="missing verifier acceptance receipts",
                actionable=True,
            )
        )
    else:
        latest = verifier_receipts[-1]
        if not latest.get("passed"):
            findings.append(
                ReviewFinding(
                    severity="critical",
                    summary="latest verifier receipt did not pass",
                    actionable=True,
                )
            )
    if "TODO" in (diff_summary or "") or "FIXME" in (diff_summary or ""):
        findings.append(
            ReviewFinding(
                severity="medium",
                summary="diff still contains TODO/FIXME markers",
                actionable=True,
            )
        )

    blocking = any(
        f.actionable and f.severity in {"critical", "high"} for f in findings
    )
    return ReviewVerdict(
        passed=not blocking,
        reviewer=reviewer,
        findings=findings,
        blocking=blocking,
    )


def can_continue_repair(state: RepairLoopState) -> tuple[bool, str]:
    if state.abandoned:
        return False, state.abandon_reason or "loop abandoned"
    if state.attempts >= state.max_attempts:
        return False, "repair attempt budget exhausted"
    if state.elapsed_seconds >= state.max_elapsed_seconds:
        return False, "repair elapsed-time budget exhausted"
    if state.tokens_used >= state.max_token_budget:
        return False, "repair token/cost budget exhausted"
    return True, "ok"


def record_repair_attempt(
    state: RepairLoopState,
    *,
    elapsed_delta_seconds: int,
    tokens_delta: int,
) -> RepairLoopState:
    state.attempts += 1
    state.elapsed_seconds += max(0, int(elapsed_delta_seconds))
    state.tokens_used += max(0, int(tokens_delta))
    return state


def remediation_loop_step(
    state: RepairLoopState,
    *,
    log_excerpt: str,
    elapsed_delta_seconds: int,
    tokens_delta: int,
) -> dict[str, Any]:
    ok, reason = can_continue_repair(state)
    if not ok:
        state.abandoned = True
        state.abandon_reason = reason
        return {
            "continue": False,
            "reason": reason,
            "diagnosis": None,
            "state": state.to_dict(),
        }
    state = record_repair_attempt(
        state,
        elapsed_delta_seconds=elapsed_delta_seconds,
        tokens_delta=tokens_delta,
    )
    diagnosis = diagnose_ci_failure(log_excerpt)
    more_ok, more_reason = can_continue_repair(state)
    if not more_ok:
        state.abandon_reason = more_reason
    return {
        "continue": True,
        "more_attempts_allowed": more_ok,
        "reason": "ok" if more_ok else more_reason,
        "diagnosis": diagnosis,
        "state": state.to_dict(),
    }


def should_publish_draft_pr(verdict: ReviewVerdict, verifier_passed: bool) -> bool:
    return bool(verifier_passed and verdict.passed and not verdict.blocking)


@dataclass
class DraftPrPlan:
    branch: str
    title: str
    body: str
    draft: bool = True
    evidence_links: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_draft_pr_plan(
    *,
    workspace_id: str,
    task_id: str,
    goal: str,
    evidence_links: list[str],
    ci_failure_seed: str | None = None,
) -> DraftPrPlan:
    title = f"task({task_id[:8]}): {goal.strip()[:72] or 'autonomous change'}"
    body_lines = [
        f"Workspace: `{workspace_id}`",
        f"Task: `{task_id}`",
        "",
        "## Evidence",
        *[f"- {link}" for link in evidence_links],
    ]
    if ci_failure_seed:
        body_lines.extend(["", "## Seeded CI failure under repair", ci_failure_seed])
    return DraftPrPlan(
        branch=f"task/{task_id}",
        title=title,
        body="\n".join(body_lines),
        draft=True,
        evidence_links=list(evidence_links),
    )


def diagnose_ci_failure(log_excerpt: str) -> dict[str, Any]:
    text = log_excerpt or ""
    if "hotspot" in text.lower() or "ratchet" in text.lower():
        return {
            "category": "file_size_ratchet",
            "repair_hint": "extract code and lower hotspot budget; never raise ratchets",
            "retryable": True,
        }
    if "typeerror" in text.lower() or "vue-tsc" in text.lower():
        return {
            "category": "typecheck",
            "repair_hint": "fix TypeScript errors on the same branch",
            "retryable": True,
        }
    if "unittest" in text.lower() or "vitest" in text.lower() or "assertionerror" in text.lower():
        return {
            "category": "tests",
            "repair_hint": "repair failing tests without weakening assertions",
            "retryable": True,
        }
    return {
        "category": "unknown",
        "repair_hint": "inspect failed job logs and repair on the same branch",
        "retryable": True,
    }
