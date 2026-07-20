"""Mandatory post-receipt Critical Review Clause for all Axon-X agents.

Canonical text matches scripts/ops/change-verify-loop.sh. Lead/Verifier LLM
builders (Gates 5–7) must call append_critical_review_clause when added.
"""

from __future__ import annotations

import re

CRITICAL_REVIEW_CLAUSE = (
    "Critically review all your previous work for factual errors, missing steps, "
    "unsupported assumptions, and any invented or unverified details. Then rewrite "
    "the answer to correct those issues and make it more precise and reliable. "
    "End with Confidence: X/10."
)

CRITICAL_REVIEW_INSTRUCTION = (
    " After all in-scope work and receipts for this turn are done, run this Critical "
    f"Review Clause as your final narrative step: {CRITICAL_REVIEW_CLAUSE} "
    "Emit the rewritten summary ending with Confidence: N/10 (integer 1-10). "
    "Runs cannot complete without that confidence line."
)

_CONFIDENCE_RE = re.compile(
    r"Confidence:\s*([1-9]|10)\s*/\s*10\b",
    re.IGNORECASE,
)

MISSING_CONFIDENCE_DETAIL = (
    "Critical Review Clause missing: final reply must end with Confidence: N/10 "
    "(integer 1-10) after the rewritten summary."
)


def append_critical_review_clause(prompt: str) -> str:
    """Append the mandatory clause instruction unless already present."""
    text = (prompt or "").rstrip()
    if not text:
        return CRITICAL_REVIEW_INSTRUCTION.strip()
    if CRITICAL_REVIEW_CLAUSE in text:
        return text
    return f"{text}{CRITICAL_REVIEW_INSTRUCTION}"


def parse_confidence(text: str) -> int | None:
    """Return the last Confidence: N/10 value in text, or None if absent/invalid."""
    matches = list(_CONFIDENCE_RE.finditer(text or ""))
    if not matches:
        return None
    return int(matches[-1].group(1))
