"""Command intent classification and human-friendly run titles."""

from __future__ import annotations

import re

_READ_PREFIX = re.compile(r"^(?:read|cat)\s+(.+)$", re.IGNORECASE)
_GIT_STATUS_PREFIX = re.compile(r"^git\s+status\b", re.IGNORECASE)
_RESUME_FROM_REVIEW = re.compile(
    r"^(?:resume(?:\s+from)?(?:\s+review|\s+review-ready)|resume-from-review)\b",
    re.IGNORECASE,
)


def classify_command(content: str) -> str:
    lowered = content.strip().lower()
    if not lowered:
        return "unsupported"

    if any(token in lowered for token in ("health", "api/health", "runtime/summary")):
        return "health_probe"
    if lowered.startswith("ls") or "list files" in lowered or lowered == "dir":
        return "list_files"
    if _READ_PREFIX.match(content.strip()) or "readme" in lowered:
        return "read_file"
    if _GIT_STATUS_PREFIX.match(content.strip()) or lowered == "git status":
        return "git_status"
    if _RESUME_FROM_REVIEW.match(content.strip()) or lowered in {
        "resume from review",
        "resume review",
        "resume-from-review",
    }:
        return "resume_from_review"
    return "unsupported"


def _extract_read_path(content: str) -> str:
    match = _READ_PREFIX.match(content.strip())
    if match:
        return match.group(1).strip()
    if "notes.txt" in content.lower():
        return "notes.txt"
    return "README.md"


def command_display_name(content: str) -> str:
    """Human-friendly run title derived from operator command text."""
    trimmed = content.strip()
    intent = classify_command(trimmed)
    if intent == "health_probe":
        return "Health check"
    if intent == "list_files":
        return "List workspace files"
    if intent == "git_status":
        return "Git status"
    if intent == "read_file":
        return f"Read {_extract_read_path(trimmed)}"
    if intent == "resume_from_review":
        return "Resume from review"
    if trimmed:
        return trimmed
    return "Operator command"


def humanize_run_summary(summary: str) -> str:
    """Best-effort friendly title for stored run summaries."""
    trimmed = summary.strip()
    if not trimmed:
        return "Operator task"
    if classify_command(trimmed) != "unsupported":
        return command_display_name(trimmed)
    return trimmed
