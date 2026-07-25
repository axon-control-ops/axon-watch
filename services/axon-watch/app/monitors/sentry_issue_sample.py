"""Extract structured Sentry issue samples from poll payloads."""

from __future__ import annotations

from typing import Any


def extract_sentry_issue_sample(
    issues: list[Any],
    *,
    limit: int = 8,
) -> list[dict[str, object]]:
    """Keep a bounded sample of unresolved issues for operator resolve actions."""
    sample: list[dict[str, object]] = []
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue_id = str(item.get("id") or "").strip()
        if not issue_id:
            continue
        sample.append(
            {
                "id": issue_id,
                "short_id": str(item.get("shortId") or item.get("short_id") or "").strip(),
                "title": str(item.get("title") or "unknown")[:160],
                "level": str(item.get("level") or "").strip(),
                "count": int(item.get("count") or 0),
                "permalink": str(item.get("permalink") or "").strip(),
                "culprit": str(item.get("culprit") or "").strip()[:160],
            }
        )
        if len(sample) >= max(1, limit):
            break
    return sample
