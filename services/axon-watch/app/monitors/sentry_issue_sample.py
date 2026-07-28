"""Extract structured Sentry issue samples from poll payloads."""

from __future__ import annotations

from typing import Any


def _release_version(raw: object) -> str:
    if isinstance(raw, dict):
        return str(raw.get("version") or raw.get("shortVersion") or "").strip()
    return str(raw or "").strip()


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
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        environment = ""
        for tag in tags:
            if not isinstance(tag, dict):
                continue
            if str(tag.get("key") or "").strip().lower() == "environment":
                environment = str(tag.get("value") or "").strip()
                break
        if not environment:
            environment = str(item.get("environment") or "").strip()
        sample.append(
            {
                "id": issue_id,
                "short_id": str(item.get("shortId") or item.get("short_id") or "").strip(),
                "title": str(item.get("title") or "unknown")[:160],
                "level": str(item.get("level") or "").strip(),
                "count": int(item.get("count") or 0),
                "permalink": str(item.get("permalink") or "").strip(),
                "culprit": str(item.get("culprit") or "").strip()[:160],
                "environment": environment,
                "first_release": _release_version(item.get("firstRelease") or item.get("first_release")),
                "last_release": _release_version(item.get("lastRelease") or item.get("last_release")),
            }
        )
        if len(sample) >= max(1, limit):
            break
    return sample
