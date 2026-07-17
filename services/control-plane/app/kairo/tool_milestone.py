"""Human-readable spoken lines for agent tool milestones."""

from __future__ import annotations

import re

_READ_RE = re.compile(r"^read\s+(.+)$", re.IGNORECASE)
_EDIT_RE = re.compile(r"^edit(?:\s+failed)?\s+(.+)$", re.IGNORECASE)
_SHELL_RE = re.compile(r"^(?:shell|run|bash)\s+(.+)$", re.IGNORECASE)
_RESEARCH_RE = re.compile(
    r"^(?:axon\s+)?research(?:\s+search)?\s+(.+)$",
    re.IGNORECASE,
)


def _short_name(path: str) -> str:
    normalized = str(path or "").strip().replace("\\", "/")
    if not normalized:
        return "that file"
    base = normalized.split("/")[-1].strip()
    return base or normalized


def _short_command(command: str) -> str:
    text = " ".join(str(command or "").split())
    if not text:
        return "that command"
    if len(text) <= 48:
        return text
    return f"{text[:45].rstrip()}…"


def contextual_tool_fallback(tool_label: str) -> str | None:
    """Turn a raw :::tool header into a short operator-facing narration line."""
    raw = str(tool_label or "").strip()
    if not raw:
        return None

    read_match = _READ_RE.match(raw)
    if read_match:
        short = _short_name(read_match.group(1))
        return f"I'm opening {short} to review what we're working with."

    edit_match = _EDIT_RE.match(raw)
    if edit_match:
        short = _short_name(edit_match.group(1))
        return f"I'm updating {short}."

    shell_match = _SHELL_RE.match(raw)
    if shell_match:
        return f"I'm running {_short_command(shell_match.group(1))} in the terminal."

    research_match = _RESEARCH_RE.match(raw)
    if research_match:
        query = research_match.group(1).strip()
        if query:
            return f"I'm searching for {query}."
        return "I'm running a research search."

    lowered = raw.lower()
    if lowered.startswith("create"):
        return "I'm putting together a plan for this."

    words = raw.split()
    if len(words) >= 2:
        action = words[0].capitalize()
        target = _short_name(" ".join(words[1:]))
        return f"{action} — working on {target}."

    return f"Working on {raw}."


__all__ = ["contextual_tool_fallback"]
