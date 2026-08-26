"""Resolve converse attachment_ids to absolute storage paths for Cursor context."""

from __future__ import annotations

from app.chat.attachment_paths import (
    AttachmentPathError,
    attachment_paths_for_ids,
    coerce_attachment_ids,
)


class ConverseAttachmentError(ValueError):
    """Invalid or foreign attachment for a VAXON converse turn."""


def attachment_paths_for_converse(
    *,
    attachment_ids: list[str],
    workspace_id: str,
) -> tuple[str, ...]:
    """Return storage paths for unbound attachments owned by the workspace."""
    try:
        return attachment_paths_for_ids(
            attachment_ids=attachment_ids,
            workspace_id=workspace_id,
            require_unbound=False,
        )
    except AttachmentPathError as exc:
        raise ConverseAttachmentError(str(exc)) from exc


def prepare_converse_attachment_paths(
    *,
    attachment_ids: list[str] | None,
    workspace_id: str,
) -> tuple[str, ...]:
    """Resolve attachment_ids or raise ConverseAttachmentError / empty tuple."""
    clean_ids = coerce_attachment_ids(attachment_ids)
    if not clean_ids:
        return ()
    return attachment_paths_for_converse(
        attachment_ids=clean_ids,
        workspace_id=workspace_id,
    )


__all__ = [
    "ConverseAttachmentError",
    "attachment_paths_for_converse",
    "coerce_attachment_ids",
    "prepare_converse_attachment_paths",
]
