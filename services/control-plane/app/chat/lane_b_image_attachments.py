"""Bridge agent-generated images into persisted chat attachments."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from app.cli_runtime.generated_image_paths import dedupe_image_paths
from app.persistence import attachment_store
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"})


def _is_image_path(value: str) -> bool:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned.startswith("http://") or cleaned.startswith("https://"):
        return False
    return Path(cleaned).suffix.lower() in _IMAGE_EXTENSIONS


def resolve_generated_image_path(
    raw_path: str,
    *,
    workspace_root: Path | None,
) -> Path | None:
    cleaned = str(raw_path or "").strip().strip("\"'")
    if not cleaned or not _is_image_path(cleaned):
        return None

    candidate = Path(cleaned).expanduser()
    if not candidate.is_absolute() and workspace_root is not None:
        candidate = (workspace_root / candidate).resolve()
    else:
        try:
            candidate = candidate.resolve()
        except OSError:
            candidate = candidate

    if candidate.is_file():
        return candidate

    if workspace_root is not None:
        basename = Path(cleaned).name
        if basename:
            workspace_candidate = (workspace_root / basename).resolve()
            if workspace_candidate.is_file():
                return workspace_candidate
            assets_candidate = (workspace_root / "assets" / basename).resolve()
            if assets_candidate.is_file():
                return assets_candidate

    return None


def ingest_agent_generated_images(
    *,
    workspace_id: str,
    message_id: str,
    thread_id: str,
    image_paths: list[str],
    created_at: str,
) -> list[dict[str, object]]:
    normalized_paths = dedupe_image_paths(image_paths)
    if not normalized_paths:
        return []

    try:
        workspace_root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        workspace_root = None

    attachment_ids: list[str] = []
    for raw_path in normalized_paths:
        resolved = resolve_generated_image_path(raw_path, workspace_root=workspace_root)
        if resolved is None:
            continue
        mime_type, _ = mimetypes.guess_type(str(resolved))
        if not mime_type or not mime_type.startswith("image/"):
            continue
        try:
            record = attachment_store.save_from_path(
                workspace_id=workspace_id,
                source_path=resolved,
                mime_type=mime_type,
                created_at=created_at,
            )
        except attachment_store.AttachmentValidationError:
            continue
        attachment_ids.append(str(record["attachment_id"]))

    if not attachment_ids:
        return []

    bound = attachment_store.bind_attachments_to_message(
        attachment_ids=attachment_ids,
        workspace_id=workspace_id,
        message_id=message_id,
        thread_id=thread_id,
    )
    return [attachment_store.serialize_attachment(item) for item in bound]
