"""Bounded Watch evidence for Sentry-aware runtime prompts."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

_SENTRY_REQUEST_RE = re.compile(r"\bsentry\b", re.IGNORECASE)


def sentry_monitor_context(
    user_prompt: str,
    *,
    fetch_monitors: Callable[..., Any],
) -> str:
    """Attach bounded, secret-free Watch evidence to Sentry agent requests."""
    if not _SENTRY_REQUEST_RE.search(user_prompt):
        return ""

    payload = fetch_monitors(timeout_seconds=2.0)
    items = payload.get("items") if isinstance(payload, dict) else None
    record = next(
        (
            item
            for item in (items if isinstance(items, list) else [])
            if isinstance(item, dict)
            and str(item.get("check_type") or "") == "sentry_recent_issues"
        ),
        None,
    )
    lines = [
        "Sentry operating rule: credentials are held by Axon Watch and intentionally "
        "excluded from workspace subprocess environment variables. Do not inspect .env, "
        "print tokens, or infer that Sentry access is missing from process.env. Use the "
        "trusted Axon Watch monitor evidence below.",
    ]
    if record:
        status = str(record.get("status") or "unknown")
        detail = str(record.get("detail") or "").strip()
        lines.append(f"Monitor status: {status}. {detail}".strip())
        issues = record.get("issues")
        if isinstance(issues, list):
            for issue in issues[:5]:
                if not isinstance(issue, dict):
                    continue
                short_id = str(issue.get("short_id") or issue.get("id") or "issue")
                title = str(issue.get("title") or "Untitled Sentry issue").strip()
                count = int(issue.get("count") or 0)
                permalink = str(issue.get("permalink") or "").strip()
                lines.append(
                    f"- {short_id}: {title} ({count} events)"
                    + (f" — {permalink}" if permalink else "")
                )
    else:
        lines.append(
            "Live monitor evidence is temporarily unavailable. Report that limitation; "
            "do not claim the Sentry token is absent."
        )
    return "\n".join(lines)
