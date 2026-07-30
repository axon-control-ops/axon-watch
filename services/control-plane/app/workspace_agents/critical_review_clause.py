"""Mandatory accuracy + Critical Review Clause for all Axon-X runtimes.

Canonical texts are shared by continuous workers, Lane B Agent/Plan/Ask/Debug,
employee persona appendices, and scripts/ops/change-verify-loop.sh (Python import).
Lead/Verifier LLM builders (Gates 5–7) must call append_critical_review_clause.
"""

from __future__ import annotations

import re

# Stable markers for idempotent append (do not rephrase these substrings lightly).
AGENT_STANDING_ACCURACY_MARKER = "Standing accuracy contract (all runtimes):"
CRITICAL_REVIEW_MARKER = "End with Confidence: X/10."

AGENT_STANDING_ACCURACY_CLAUSE = (
    f"{AGENT_STANDING_ACCURACY_MARKER} "
    "Act as the lead engineer for your field with 20+ years of professional experience. "
    "Never hallucinate — do not invent APIs, file contents, logs, receipts, URLs, "
    "commands, or outcomes. Never present guesses or unverified assumptions as facts. "
    "Treat the assigned task/goal and operator instructions as the sole truth for scope; "
    "do not derail onto unrelated work. Prefer verified local evidence (repo, command "
    "output, receipts). Where necessary and possible, consult online proven sources or "
    "official documentation before asserting external/vendor facts; if you cannot verify, "
    "say so plainly. Suggest concrete improvements or next steps when they strengthen the "
    "outcome without expanding scope. Robust accuracy over speed."
)

CRITICAL_REVIEW_CLAUSE = (
    "Critically review all your previous work for factual errors, missing steps, "
    "unsupported assumptions, invented or unverified details, and any hallucination. "
    "Where necessary and possible, cross-check claims against local receipts and online "
    "proven sources or official documentation. Act as the lead engineer for this field "
    "with 20+ years of experience: suggest improvements or precise next-step "
    "recommendations. Then rewrite the answer to correct those issues and make it more "
    "precise and reliable. Never invent facts in the rewrite. "
    f"{CRITICAL_REVIEW_MARKER}"
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


def _has_standing_accuracy(text: str) -> bool:
    return AGENT_STANDING_ACCURACY_MARKER in (text or "")


def _has_critical_review(text: str) -> bool:
    hay = text or ""
    return CRITICAL_REVIEW_MARKER in hay or CRITICAL_REVIEW_CLAUSE in hay


def append_agent_standing_accuracy_clause(prompt: str) -> str:
    """Append the standing no-hallucination / lead-engineer contract unless present."""
    text = (prompt or "").rstrip()
    if _has_standing_accuracy(text):
        return text or AGENT_STANDING_ACCURACY_CLAUSE
    if not text:
        return AGENT_STANDING_ACCURACY_CLAUSE
    return f"{text} {AGENT_STANDING_ACCURACY_CLAUSE}"


def append_critical_review_clause(prompt: str) -> str:
    """Append standing accuracy + mandatory Critical Review unless already present.

    All runtime prompt builders should call this helper so Ask/Plan/Debug/Agent
    and continuous workers share the same hardened contracts.
    """
    text = append_agent_standing_accuracy_clause(prompt)
    if _has_critical_review(text):
        return text
    if not text:
        return (
            f"{AGENT_STANDING_ACCURACY_CLAUSE}{CRITICAL_REVIEW_INSTRUCTION}"
        ).strip()
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


__all__ = [
    "AGENT_STANDING_ACCURACY_CLAUSE",
    "AGENT_STANDING_ACCURACY_MARKER",
    "AUTO_RECOVERED_CONFIDENCE",
    "CRITICAL_REVIEW_CLAUSE",
    "CRITICAL_REVIEW_INSTRUCTION",
    "CRITICAL_REVIEW_MARKER",
    "MISSING_CONFIDENCE_DETAIL",
    "append_agent_standing_accuracy_clause",
    "append_critical_review_clause",
    "critical_review_receipt_summary",
    "parse_confidence",
    "resolve_critical_review_confidence",
]
