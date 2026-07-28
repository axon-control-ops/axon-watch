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

# Accept "Confidence: 8/10" and the common miss "Confidence 8/10".
_CONFIDENCE_RE = re.compile(
    r"Confidence:?\s*([1-9]|10)\s*/\s*10\b",
    re.IGNORECASE,
)

MISSING_CONFIDENCE_DETAIL = (
    "Critical Review Clause missing: final reply must end with Confidence: N/10 "
    "(integer 1-10) after the rewritten summary."
)

# When the agent did real work but forgot the closing score, auto-recover so the
# operator does not get stuck on a red Try-again strip for a formatting miss.
AUTO_RECOVERED_CONFIDENCE = 6
_MIN_SUBSTANTIVE_REPLY_CHARS = 280
_THINKING_BLOCK_RE = re.compile(r":::thinking\b[\s\S]*?(?:::|\Z)", re.IGNORECASE)


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


def _substantive_reply_body(text: str) -> str:
    cleaned = _THINKING_BLOCK_RE.sub(" ", text or "")
    return " ".join(cleaned.split()).strip()


def resolve_critical_review_confidence(reply_text: str) -> tuple[int | None, bool]:
    """Return ``(confidence, auto_recovered)``.

    Explicit Confidence wins. Substantive replies that omit the closing line are
    auto-scored so roster/error strips do not demand a manual Try again for a
    formatting miss. Empty / trivial replies still fail closed.
    """
    parsed = parse_confidence(reply_text)
    if parsed is not None:
        return parsed, False
    body = _substantive_reply_body(reply_text)
    if len(body) >= _MIN_SUBSTANTIVE_REPLY_CHARS:
        return AUTO_RECOVERED_CONFIDENCE, True
    return None, False


def critical_review_receipt_summary(confidence: int, *, auto_recovered: bool) -> str:
    if auto_recovered:
        return (
            f"Critical Review Confidence: {confidence}/10 "
            "(auto-recovered — closing Confidence line was missing)"
        )
    return f"Critical Review Confidence: {confidence}/10"
