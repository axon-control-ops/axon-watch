"""Inbox ranking for watch-produced signals without mutating item schema."""

from __future__ import annotations

_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "warning": 2,
    "info": 3,
}


def severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity, len(_SEVERITY_RANK))


def rank_inbox_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    # Stable two-pass ordering: newest first within a severity band, then higher
    # severities first across the whole inbox.
    ranked_by_recency = sorted(
        items,
        key=lambda item: str(item.get("updated_at", "")),
        reverse=True,
    )
    return sorted(
        ranked_by_recency,
        key=lambda item: severity_rank(str(item.get("severity", ""))),
    )
