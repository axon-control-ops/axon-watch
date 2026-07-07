"""Command intent classification and human-friendly run titles."""

from __future__ import annotations

import re

_READ_PREFIX = re.compile(r"^(?:read|cat)\s+(.+)$", re.IGNORECASE)
_GIT_STATUS_PREFIX = re.compile(r"^git\s+status\b", re.IGNORECASE)
_RESUME_FROM_REVIEW = re.compile(
    r"^(?:resume(?:\s+from)?(?:\s+review|\s+review-ready)|resume-from-review)\b",
    re.IGNORECASE,
)
_RUN_PREFIX = re.compile(r"^run\s+.+", re.IGNORECASE)
# Questions must be answered by the runtime, never executed as commands.
# "did you commit?" or "what does the README say?" are conversation, while
# "read README.md" or "git status" are imperative operator commands.
_QUESTION_PREFIX = re.compile(
    r"^\s*(?:did|do|does|have|has|had|is|are|was|were|can|could|will|would|"
    r"should|shall|what|when|where|which|who|why|how)\b",
    re.IGNORECASE,
)


def is_question(content: str) -> bool:
    stripped = content.strip()
    if stripped.endswith("?"):
        return True
    return bool(_QUESTION_PREFIX.match(stripped))
_SHORTCUT_SHELL_COMMANDS = {
    "check-health": "./scripts/dev/check-health.sh",
    "check health": "./scripts/dev/check-health.sh",
    "ota": "npm run ota:canary",
    "ota canary": "npm run ota:canary",
    "dashpro ota": "npm run ota:canary",
    "dashpro ota canary": "npm run ota:canary",
    "verify": "npm run verify:production-operator",
}


def expand_command_shortcuts(content: str) -> str:
    """Map allowlisted operator shortcuts to bounded `run …` shell commands."""
    trimmed = content.strip()
    mapped = _SHORTCUT_SHELL_COMMANDS.get(trimmed.lower())
    if mapped is None:
        return trimmed
    return f"run {mapped}"


def classify_command(content: str) -> str:
    lowered = content.strip().lower()
    if not lowered:
        return "unsupported"

    if is_question(content):
        return "unsupported"

    if lowered in _SHORTCUT_SHELL_COMMANDS:
        return "shell_command"
    if _RUN_PREFIX.match(content.strip()):
        return "shell_command"

    if lowered in {"health", "api/health"} or "api/health" in lowered or lowered == "runtime/summary":
        return "health_probe"
    if lowered.startswith("ls") or "list files" in lowered or lowered == "dir":
        return "list_files"
    if _READ_PREFIX.match(content.strip()) or re.match(
        r"^(?:open|show)\s+(?:the\s+)?readme\b", lowered
    ):
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
    if intent == "shell_command":
        from app.chat.shell_command import extract_shell_command_line

        command_line = extract_shell_command_line(expand_command_shortcuts(trimmed)) or trimmed
        return f"Run {command_line}"
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
