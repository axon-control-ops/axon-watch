"""Prompt text for files copied into a worker sandbox."""

from __future__ import annotations


def format_task_attachment_clause(attachment_paths: list[str] | None) -> str:
    paths = [str(path).strip() for path in (attachment_paths or []) if str(path).strip()]
    if not paths:
        return ""
    joined = ", ".join(f"`{path}`" for path in paths[:8])
    suffix = "..." if len(paths) > 8 else ""
    return (
        f" Attached files available in this sandbox: {joined}{suffix}. "
        "Open these paths directly before judging screenshot or document content."
    )


__all__ = ["format_task_attachment_clause"]
