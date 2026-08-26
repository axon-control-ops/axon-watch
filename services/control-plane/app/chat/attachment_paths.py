"""Attachment path helpers shared by interactive and worker chat dispatch."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.persistence import attachment_store


class AttachmentPathError(ValueError):
    """Attachment id is missing, foreign, already bound, or otherwise unusable."""


def coerce_attachment_ids(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    attachment_ids: list[str] = []
    for item in raw:
        clean = str(item or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        attachment_ids.append(clean)
    return attachment_ids


def attachment_paths_for_ids(
    *,
    attachment_ids: list[str],
    workspace_id: str,
    require_unbound: bool = True,
) -> tuple[str, ...]:
    clean_ids = coerce_attachment_ids(attachment_ids)
    if not clean_ids:
        return ()
    clean_workspace = str(workspace_id or "").strip()
    if not clean_workspace:
        raise AttachmentPathError("workspace_id is required for attachments")
    paths: list[str] = []
    for attachment_id in clean_ids:
        record = attachment_store.get_attachment(attachment_id)
        if record is None:
            raise AttachmentPathError(f"attachment not found: {attachment_id}")
        if str(record.get("workspace_id") or "") != clean_workspace:
            raise AttachmentPathError("attachment does not belong to workspace")
        if require_unbound and record.get("message_id"):
            raise AttachmentPathError("attachment is already linked to a message")
        paths.append(str(record["storage_path"]))
    return tuple(paths)


def localize_attachment_paths_for_sandbox(
    paths: tuple[str, ...],
    *,
    sandbox_workspace_root: Path | None,
) -> tuple[str, ...]:
    """Copy attachments into the agent sandbox and return reachable paths."""
    if not paths or sandbox_workspace_root is None:
        return paths
    dest_dir = sandbox_workspace_root / ".attachments"
    localized: list[str] = []
    for raw_path in paths:
        source = Path(raw_path)
        try:
            if not source.is_file():
                localized.append(raw_path)
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / source.name
            shutil.copy2(source, dest)
            localized.append(str(dest))
        except OSError:
            localized.append(raw_path)
    return tuple(localized)


def localized_attachment_paths_for_ids(
    *,
    attachment_ids: list[str] | None,
    workspace_id: str,
    sandbox_workspace_root: Path | None,
    require_unbound: bool = True,
) -> tuple[str, ...]:
    paths = attachment_paths_for_ids(
        attachment_ids=coerce_attachment_ids(attachment_ids),
        workspace_id=workspace_id,
        require_unbound=require_unbound,
    )
    return localize_attachment_paths_for_sandbox(
        paths,
        sandbox_workspace_root=sandbox_workspace_root,
    )


__all__ = [
    "AttachmentPathError",
    "attachment_paths_for_ids",
    "coerce_attachment_ids",
    "localized_attachment_paths_for_ids",
    "localize_attachment_paths_for_sandbox",
]
