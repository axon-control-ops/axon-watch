"""Goal-text overlap helpers for Lead queue supersede / duplicate cleanup."""

from __future__ import annotations

import re

_CONFIRM_PREFIX_RE = re.compile(
    r"^\s*please\s+confirm\s+if\s+we\s+did\s+this\s+job\s*['\"]?",
    re.I,
)
_DEDUPE_KEY_RE = re.compile(
    r"(?:dedupe_key|\[dedupe\])[=:\s]+([a-z0-9:._\-]+)",
    re.I,
)
_LEAD_FOLLOWUP_RE = re.compile(
    r"^\s*lead\s+(?:follow-up\s+after|:\s*advance)\b",
    re.I,
)


def normalize_goal_core(goal: str) -> str:
    cleaned = " ".join(str(goal or "").strip().split()).lower()
    cleaned = _CONFIRM_PREFIX_RE.sub("", cleaned).strip(" '\"")
    return cleaned


def token_set(text: str) -> set[str]:
    tokens: set[str] = set()
    for tok in re.findall(r"[a-z0-9]{3,}", text.lower()):
        tokens.add(tok)
        if len(tok) > 4 and tok.endswith("s"):
            tokens.add(tok[:-1])
    return tokens


def extract_dedupe_key(goal: str) -> str:
    match = _DEDUPE_KEY_RE.search(str(goal or ""))
    return (match.group(1) if match else "").strip().lower()


def is_lead_follow_up_goal(goal: str) -> bool:
    return bool(_LEAD_FOLLOWUP_RE.search(str(goal or "")))


def goals_overlap(
    left: str,
    right: str,
    *,
    threshold: float = 0.45,
    min_core_len: int = 12,
    min_tokens: int = 2,
) -> bool:
    left_core = normalize_goal_core(left)
    right_core = normalize_goal_core(right)
    if len(left_core) < min_core_len or len(right_core) < min_core_len:
        return False
    left_key = extract_dedupe_key(left)
    right_key = extract_dedupe_key(right)
    if left_key and right_key and left_key == right_key:
        return True
    left_tokens = token_set(left_core)
    right_tokens = token_set(right_core)
    if len(left_tokens) < min_tokens or len(right_tokens) < min_tokens:
        return False
    nested = left_core in right_core or right_core in left_core
    if nested:
        return True
    overlap = len(left_tokens & right_tokens) / float(
        min(len(left_tokens), len(right_tokens))
    )
    return overlap >= threshold


__all__ = [
    "extract_dedupe_key",
    "goals_overlap",
    "is_lead_follow_up_goal",
    "normalize_goal_core",
    "token_set",
]
