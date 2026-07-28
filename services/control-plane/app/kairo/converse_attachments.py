"""Resolve converse attachment_ids to absolute storage paths for Cursor context."""

from __future__ import annotations

from app.persistence import attachment_store


class ConverseAttachmentError(ValueError):
    """Invalid or foreign attachment for a VAXON converse turn."""


def coerce_attachment_ids(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        clean = str(item or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
    return out


def attachment_paths_for_converse(
    *,
    attachment_ids: list[str],
    workspace_id: str,
) -> tuple[str, ...]:
    """Return storage paths for unbound attachments owned by the workspace."""
    clean_ids = coerce_attachment_ids(attachment_ids)
    if not clean_ids:
        return ()
    clean_workspace = str(workspace_id or "").strip()
    if not clean_workspace:
        raise ConverseAttachmentError("workspace_id is required for attachments")

    paths: list[str] = []
    for attachment_id in clean_ids:
        record = attachment_store.get_attachment(attachment_id)
        if record is None:
            raise ConverseAttachmentError(f"attachment not found: {attachment_id}")
        if str(record.get("workspace_id") or "") != clean_workspace:
            raise ConverseAttachmentError("attachment does not belong to workspace")
        paths.append(str(record["storage_path"]))
    return tuple(paths)


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
