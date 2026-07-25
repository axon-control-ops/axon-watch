"""Deterministic verification against named regression thresholds."""

from __future__ import annotations

from app.safe_improvement.models import EvaluationCase, VerificationResult


def evaluate_against_threshold(
    case: EvaluationCase,
    *,
    baseline_value: float,
    candidate_value: float,
) -> VerificationResult:
    threshold = float(case.threshold)
    comparator = case.comparator
    if comparator == "lte":
        # Candidate must not regress beyond baseline by more than threshold delta.
        delta = candidate_value - baseline_value
        passed = delta <= threshold
        reason = (
            f"delta {delta:.4f} <= threshold {threshold:.4f}"
            if passed
            else f"regression delta {delta:.4f} exceeds threshold {threshold:.4f}"
        )
    elif comparator == "gte":
        delta = baseline_value - candidate_value
        passed = delta <= threshold
        reason = (
            f"drop {delta:.4f} <= threshold {threshold:.4f}"
            if passed
            else f"metric drop {delta:.4f} exceeds threshold {threshold:.4f}"
        )
    elif comparator == "eq":
        passed = abs(candidate_value - baseline_value) <= threshold
        reason = (
            f"|diff| within {threshold:.4f}"
            if passed
            else f"|diff| exceeds equality threshold {threshold:.4f}"
        )
    else:
        passed = False
        reason = f"unsupported comparator `{comparator}`"

    return VerificationResult(
        passed=passed,
        metric=case.metric,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        threshold=threshold,
        comparator=comparator,
        reason=reason,
    )
