"""Persisted chat attachments for Lane B composer uploads (images + documents)."""

from __future__ import annotations

import mimetypes
import os
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite

_ATTACHMENT_COLUMNS = (
    "attachment_id",
    "workspace_id",
    "message_id",
    "thread_id",
    "filename",
    "mime_type",
    "storage_path",
    "created_at",
)

_MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
_ALLOWED_MIME_PREFIXES = ("image/",)
_ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/csv",
        "application/json",
        "application/vnd.ms-excel",
        "text/csv",
        "text/tab-separated-values",
        "text/plain",
        "text/markdown",
    }
)
_GENERIC_UPLOAD_MIME_TYPES = frozenset(
    {
        "",
        "application/octet-stream",
        "binary/octet-stream",
    }
)
_EXTENSION_MIME_TYPES = {
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".json": "application/json",
}


class AttachmentNotFoundError(LookupError):
    pass


class AttachmentValidationError(ValueError):
    pass


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _state_dir() -> Path:
    raw = os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state").strip() or "./.local/state"
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[4] / raw).resolve()


def _attachments_root() -> Path:
    root = _state_dir() / "chat-attachments"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def _row_to_record(row: Any) -> dict[str, Any]:
    return {
        "attachment_id": row["attachment_id"],
        "workspace_id": row["workspace_id"],
        "message_id": row["message_id"],
        "thread_id": row["thread_id"],
        "filename": row["filename"],
        "mime_type": row["mime_type"],
        "storage_path": row["storage_path"],
        "created_at": row["created_at"],
    }


def _guess_mime_from_filename(filename: str) -> str:
    suffix = Path(str(filename or "").strip()).suffix.lower()
    if suffix in _EXTENSION_MIME_TYPES:
        return _EXTENSION_MIME_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(str(filename or ""))
    return str(guessed or "").strip().lower()


def _resolve_mime_type(filename: str, mime_type: str) -> str:
    clean = str(mime_type or "").strip().lower()
    if clean not in _GENERIC_UPLOAD_MIME_TYPES:
        return clean
    guessed = _guess_mime_from_filename(filename)
    return guessed or clean


def _validate_mime_type(mime_type: str) -> str:
    clean = str(mime_type or "").strip().lower()
    if not clean:
        raise AttachmentValidationError("attachment mime_type is required")
    if clean in _ALLOWED_MIME_TYPES:
        return clean
    if any(clean.startswith(prefix) for prefix in _ALLOWED_MIME_PREFIXES):
        return clean
    raise AttachmentValidationError(
        "unsupported attachment type (images, PDF, CSV, and text files are allowed)"
    )


def _safe_filename(filename: str, mime_type: str) -> str:
    base = Path(str(filename or "attachment").strip()).name or "attachment"
    if "." not in base:
        extension = mimetypes.guess_extension(mime_type) or ".bin"
        base = f"{base}{extension}"
    return base[:180]


def save_from_path(
    *,
    workspace_id: str,
    source_path: str | Path,
    mime_type: str,
    created_at: str,
    filename: str | None = None,
) -> dict[str, Any]:
    path = Path(source_path).expanduser()
    if not path.is_file():
        raise AttachmentValidationError("attachment source file not found")
    data = path.read_bytes()
    chosen_name = filename or path.name
    return save_upload(
        workspace_id=workspace_id,
        filename=chosen_name,
        mime_type=mime_type,
        data=data,
        created_at=created_at,
    )


def save_upload(
    *,
    workspace_id: str,
    filename: str,
    mime_type: str,
    data: bytes,
    created_at: str,
) -> dict[str, Any]:
    clean_workspace_id = str(workspace_id or "").strip()
    if not clean_workspace_id:
        raise AttachmentValidationError("workspace_id is required")
    if not data:
        raise AttachmentValidationError("attachment payload is empty")
    if len(data) > _MAX_ATTACHMENT_BYTES:
        raise AttachmentValidationError("attachment exceeds 8MB limit")

    clean_mime = _validate_mime_type(_resolve_mime_type(filename, mime_type))
    safe_name = _safe_filename(filename, clean_mime)
    attachment_id = f"attachment_{uuid4().hex}"
    workspace_dir = _attachments_root() / clean_workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    storage_path = workspace_dir / f"{attachment_id}_{safe_name}"
    storage_path.write_bytes(data)

    record = {
        "attachment_id": attachment_id,
        "workspace_id": clean_workspace_id,
        "message_id": None,
        "thread_id": None,
        "filename": safe_name,
        "mime_type": clean_mime,
        "storage_path": str(storage_path),
        "created_at": created_at,
    }
    with _managed_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO chat_attachments ({", ".join(_ATTACHMENT_COLUMNS)})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["attachment_id"],
                record["workspace_id"],
                record["message_id"],
                record["thread_id"],
                record["filename"],
                record["mime_type"],
                record["storage_path"],
                record["created_at"],
            ),
        )
        connection.commit()
    return deepcopy(record)


def get_attachment(attachment_id: str) -> dict[str, Any] | None:
    clean_id = str(attachment_id or "").strip()
    if not clean_id:
        return None
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM chat_attachments WHERE attachment_id = ?",
            (clean_id,),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def require_attachment(attachment_id: str) -> dict[str, Any]:
    record = get_attachment(attachment_id)
    if record is None:
        raise AttachmentNotFoundError(f"attachment not found: {attachment_id}")
    return record


def bind_attachments_to_message(
    *,
    attachment_ids: list[str],
    workspace_id: str,
    message_id: str,
    thread_id: str,
) -> list[dict[str, Any]]:
    clean_ids = [str(item).strip() for item in attachment_ids if str(item).strip()]
    if not clean_ids:
        return []

    bound: list[dict[str, Any]] = []
    with _managed_connection() as connection:
        for attachment_id in clean_ids:
            row = connection.execute(
                "SELECT * FROM chat_attachments WHERE attachment_id = ?",
                (attachment_id,),
            ).fetchone()
            if row is None:
                raise AttachmentNotFoundError(f"attachment not found: {attachment_id}")
            record = _row_to_record(row)
            if record["workspace_id"] != workspace_id:
                raise AttachmentValidationError("attachment does not belong to workspace")
            if record["message_id"]:
                raise AttachmentValidationError("attachment is already linked to a message")
            connection.execute(
                """
                UPDATE chat_attachments
                SET message_id = ?, thread_id = ?
                WHERE attachment_id = ?
                """,
                (message_id, thread_id, attachment_id),
            )
            record["message_id"] = message_id
            record["thread_id"] = thread_id
            bound.append(record)
        connection.commit()
    return bound


def list_attachments_for_messages(message_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    clean_ids = [str(item).strip() for item in message_ids if str(item).strip()]
    if not clean_ids:
        return {}

    placeholders = ", ".join("?" for _ in clean_ids)
    with _managed_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM chat_attachments
            WHERE message_id IN ({placeholders})
            ORDER BY created_at ASC, attachment_id ASC
            """,
            clean_ids,
        ).fetchall()

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        record = _row_to_record(row)
        message_id = str(record["message_id"] or "")
        grouped.setdefault(message_id, []).append(record)
    return grouped


def public_attachment_url(attachment_id: str) -> str:
    encoded = str(attachment_id or "").strip()
    return f"/api/chat/attachments/{encoded}"


def serialize_attachment(record: dict[str, Any]) -> dict[str, Any]:
    attachment_id = str(record["attachment_id"])
    return {
        "attachment_id": attachment_id,
        "workspace_id": record["workspace_id"],
        "message_id": record.get("message_id"),
        "thread_id": record.get("thread_id"),
        "filename": record["filename"],
        "mime_type": record["mime_type"],
        "url": public_attachment_url(attachment_id),
        "created_at": record["created_at"],
    }
