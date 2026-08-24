"""Command intent classification and human-friendly run titles."""

from __future__ import annotations

import re

from app.chat.move_voice_orb import is_move_voice_orb_command

_READ_PREFIX = re.compile(r"^(?:read|cat)\s+(.+)$", re.IGNORECASE)
_GIT_STATUS_PREFIX = re.compile(r"^git\s+status\b", re.IGNORECASE)
_RESUME_FROM_REVIEW = re.compile(
    r"^(?:resume(?:\s+from)?(?:\s+review|\s+review-ready)|resume-from-review)\b",
    re.IGNORECASE,
)
_RUN_PREFIX = re.compile(r"^run\s+.+", re.IGNORECASE)
_QUESTION_COMMAND_OVERRIDES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"^\s*(?:what(?:'s| is)|show|give|tell)\s+(?:me\s+)?(?:the\s+)?git\s+status\b\??\s*$",
            re.IGNORECASE,
        ),
        "git status",
    ),
    (
        re.compile(
            r"^\s*can\s+you\s+(?:run|check|show)\s+(?:me\s+)?(?:the\s+)?git\s+status\b\??\s*$",
            re.IGNORECASE,
        ),
        "git status",
    ),
)
# Questions must be answered by the runtime, never executed as commands.
# "did you commit?" or "what does the README say?" are conversation, while
# "read README.md" or "git status" are imperative operator commands.
AUTO_COMPLETE_COMMAND_INTENTS = frozenset(
    {
        "git_status",
        "health_probe",
        "list_files",
        "read_file",
        "move_voice_orb",
    }
)

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
    "mobile dev": "npm run dev:console-mobile",
    "console mobile dev": "npm run dev:console-mobile",
    "start mobile app": "npm run dev:console-mobile",
    "start console mobile": "npm run dev:console-mobile",
}

# Read-only shell shortcuts that may auto-dispatch / auto-complete like health_probe.
_REVERSIBLE_SHELL_SCRIPTS = frozenset(
    {
        "./scripts/dev/check-health.sh",
    }
)


def expand_command_shortcuts(content: str) -> str:
    """Normalize allowlisted shortcuts and explicit question-commands."""
    trimmed = content.strip()
    for pattern, replacement in _QUESTION_COMMAND_OVERRIDES:
        if pattern.match(trimmed):
            return replacement
    mapped = _SHORTCUT_SHELL_COMMANDS.get(trimmed.lower())
    if mapped is None:
        return trimmed
    return f"run {mapped}"


def _shell_script_from_run_command(content: str) -> str | None:
    match = re.match(r"^run\s+(.+)$", content.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def is_reversible_shell_command(content: str) -> bool:
    """True for allowlisted read-only shell shortcuts (e.g. check-health)."""
    normalized = expand_command_shortcuts(content.strip())
    script = _shell_script_from_run_command(normalized)
    return bool(script and script in _REVERSIBLE_SHELL_SCRIPTS)


def is_auto_complete_run_summary(summary: str) -> bool:
    """True when a run summary maps to a read-only one-shot operator command."""
    trimmed = summary.strip()
    if not trimmed:
        return False
    intent = classify_command(trimmed)
    if intent in AUTO_COMPLETE_COMMAND_INTENTS:
        return True
    return intent == "shell_command" and is_reversible_shell_command(trimmed)


def command_requires_confirmation(content: str) -> bool:
    """True when an operator command must be confirmed before dispatch."""
    normalized = expand_command_shortcuts(content.strip())
    if not normalized:
        return True
    intent = classify_command(normalized)
    if intent in AUTO_COMPLETE_COMMAND_INTENTS:
        return False
    if intent == "shell_command" and is_reversible_shell_command(normalized):
        return False
    return True


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
    if is_move_voice_orb_command(content):
        return "move_voice_orb"
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
    if intent == "move_voice_orb":
        return "Move voice orb"
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
