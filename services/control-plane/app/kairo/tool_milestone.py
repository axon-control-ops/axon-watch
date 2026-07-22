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
_AMBIENT_DOC_RE = re.compile(
    r"^(operations|readme|agents|claude|contributing|changelog|license)"
    r"(?:\.(md|txt|rst))?$",
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


def _clean_prompt(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _prompt_snippet(prompt: str, max_len: int = 42) -> str:
    if not prompt:
        return ""
    if len(prompt) <= max_len:
        return prompt
    return f"{prompt[: max_len - 1].rstrip()}…"


def _task_hint(operator_prompt: str | None = None, task_summary: str | None = None) -> str:
    summary = _clean_prompt(task_summary)
    if summary and not re.match(r"^(thinking|done|failed)", summary, re.IGNORECASE):
        return _prompt_snippet(summary, 56)
    return _prompt_snippet(_clean_prompt(operator_prompt), 56)


def contextual_tool_fallback(
    tool_label: str,
    *,
    operator_prompt: str | None = None,
    task_summary: str | None = None,
) -> str | None:
    """Turn a raw :::tool header into a short operator-facing narration line.

    Returns None when the tool is ambient orientation noise (skip speaking).
    """
    raw = str(tool_label or "").strip()
    if not raw:
        return None

    hint = _task_hint(operator_prompt, task_summary)

    read_match = _READ_RE.match(raw)
    if read_match:
        short = _short_name(read_match.group(1))
        if _AMBIENT_DOC_RE.match(short):
            return None
        if hint:
            return f"Checking {short} for: {hint}"
        return f"Checking {short}."

    edit_match = _EDIT_RE.match(raw)
    if edit_match:
        short = _short_name(edit_match.group(1))
        if hint:
            return f"Updating {short} — {hint}"
        return f"Updating {short}."

    shell_match = _SHELL_RE.match(raw)
    if shell_match:
        command = _short_command(shell_match.group(1))
        lowered = command.lower()
        if re.search(r"\b(eas\s+update|ota|expo\s+publish)\b", lowered):
            return f"Running the production OTA — {hint}" if hint else "Running the production OTA in the terminal."
        if re.search(r"\b(poll|watch|tail|sleep)\b", lowered):
            return f"Still monitoring — {hint}" if hint else f"Monitoring terminal output from {command}."
        if hint:
            return f"Running {command} — {hint}"
        return f"Running {command} in the terminal."

    research_match = _RESEARCH_RE.match(raw)
    if research_match:
        query = research_match.group(1).strip()
        if query:
            return f"Searching for {query}."
        return "Running a research search."

    lowered = raw.lower()
    if lowered.startswith("create"):
        return f"Drafting a plan for: {hint}" if hint else "Putting together a plan for this."

    words = raw.split()
    if len(words) >= 2:
        action = words[0].capitalize()
        target = _short_name(" ".join(words[1:]))
        if hint:
            return f"{action} {target} — {hint}"
        return f"{action} — working on {target}."

    if hint:
        return f"Working on {raw} — {hint}"
    return f"Working on {raw}."


__all__ = ["contextual_tool_fallback"]
