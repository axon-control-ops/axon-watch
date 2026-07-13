"""Pack recent IDE thread turns into Lane B Cursor context (C10/M4 completion)."""

from __future__ import annotations

from typing import Any

_DEFAULT_MAX_MESSAGES = 6
_DEFAULT_MAX_CHARS = 1200
_ALLOWED_ROLES = frozenset({"operator", "agent"})


def build_lane_b_thread_context_appendix(
    messages: list[dict[str, Any]],
    *,
    max_messages: int = _DEFAULT_MAX_MESSAGES,
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> str:
    """Return a capped transcript of recent operator/agent turns for Lane B prompts.

    System rows and empty agent placeholders are skipped. History is
    non-authoritative context — the current operator request remains primary.
    """
    selected: list[tuple[str, str]] = []
    for item in messages:
        role = str(item.get("role") or "").strip().lower()
        if role not in _ALLOWED_ROLES:
            continue
        content = " ".join(str(item.get("content") or "").split()).strip()
        if not content:
            continue
        selected.append((role, content))

    if not selected:
        return ""

    selected = selected[-max(1, int(max_messages)) :]
    lines = ["Recent IDE thread (non-authoritative):"]
    for role, content in selected:
        lines.append(f"- {role}: {content}")
    appendix = "\n".join(lines)
    limit = max(80, int(max_chars))
    if len(appendix) <= limit:
        return appendix
    return f"{appendix[: limit - 1].rstrip()}…"
