"""List, read, and write workspace-scoped files."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path

from app.terminal.workspace_roots import resolve_workspace_root
from app.workspace_catalog import get_workspace_record


class WorkspaceFileError(ValueError):
    pass


class WorkspaceFileConflictError(WorkspaceFileError):
    """Raised when a save's base_sha256 no longer matches the file on disk —
    someone else (an agent, another operator tab) changed it since it was loaded."""


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


_SKIPPED_DIRECTORY_NAMES = {
    "__pycache__",
    "coverage",
    "dist",
    "build",
    "node_modules",
    "venv",
}
_MAX_LISTED_FILES = 5000
_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".avif"})
_BINARY_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".zip",
        ".gz",
        ".tgz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".wasm",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".ico",
        ".mp3",
        ".mp4",
        ".webm",
        ".mov",
        ".avi",
        ".wav",
        ".ogg",
        ".sqlite",
        ".sqlite3",
        ".db",
        ".apk",
        ".aab",
        ".dmg",
        ".iso",
    }
)
_MAX_RAW_FILE_BYTES = 16 * 1024 * 1024
_MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024


def is_image_workspace_file(file_path: str) -> bool:
    return Path(str(file_path or "").strip()).suffix.lower() in _IMAGE_EXTENSIONS


def is_binary_workspace_file(file_path: str) -> bool:
    suffix = Path(str(file_path or "").strip()).suffix.lower()
    return suffix in _IMAGE_EXTENSIONS or suffix in _BINARY_EXTENSIONS


def workspace_file_media_type(file_path: str) -> str:
    guessed, _ = mimetypes.guess_type(str(file_path or "").strip())
    if guessed:
        return guessed
    return "application/octet-stream"


def _safe_resolve(workspace_root: Path, relative_path: str) -> Path:
    relative_path = relative_path.strip().lstrip("/")
    if not relative_path:
        raise WorkspaceFileError("file path is required")
    if ".." in Path(relative_path).parts:
        raise WorkspaceFileError("path traversal is not allowed")

    root = workspace_root.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise WorkspaceFileError("path escapes workspace root") from exc
    return target


def ensure_bootstrap_files(workspace_id: str) -> Path:
    get_workspace_record(workspace_id)
    root = resolve_workspace_root(workspace_id)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "\n".join(
                [
                    f"# {workspace_id}",
                    "",
                    "This file lives on disk under the workspace root.",
                    "Edit it in the Monaco editor and save with the Save button.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    notes = root / "notes.txt"
    if not notes.exists():
        notes.write_text("Workspace notes go here.\n", encoding="utf-8")
    return root


def _should_skip_directory(name: str) -> bool:
    return name.startswith(".") or name in _SKIPPED_DIRECTORY_NAMES


def _should_skip_file(name: str) -> bool:
    return name.startswith(".")


def list_workspace_files(workspace_id: str) -> list[dict[str, object]]:
    root = ensure_bootstrap_files(workspace_id)
    items: list[dict[str, object]] = []
    for current_root, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = sorted(
            directory for directory in dirnames if not _should_skip_directory(directory)
        )
        for filename in sorted(filenames):
            if _should_skip_file(filename):
                continue
            path = Path(current_root) / filename
            relative = path.relative_to(root).as_posix()
            items.append(
                {
                    "path": relative,
                    "size_bytes": path.stat().st_size,
                }
            )
            if len(items) >= _MAX_LISTED_FILES:
                return items
    return items


def resolve_workspace_file_path(workspace_id: str, file_path: str) -> Path:
    root = resolve_workspace_root(workspace_id)
    target = _safe_resolve(root, file_path)
    if not target.is_file():
        raise WorkspaceFileError(f"file not found: {file_path}")
    return target


def read_workspace_file(workspace_id: str, file_path: str) -> dict[str, object]:
    target = resolve_workspace_file_path(workspace_id, file_path)
    if is_binary_workspace_file(file_path):
        raise WorkspaceFileError("binary files must be fetched via the raw file endpoint")
    size_bytes = target.stat().st_size
    if size_bytes > _MAX_TEXT_FILE_BYTES:
        raise WorkspaceFileError("text file exceeds 2MB editor limit")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceFileError(
            "binary files must be fetched via the raw file endpoint"
        ) from exc
    return {
        "workspace_id": workspace_id,
        "path": file_path,
        "content": content,
        "size_bytes": size_bytes,
        "content_sha256": _content_sha256(content),
    }


def read_workspace_file_bytes(workspace_id: str, file_path: str) -> tuple[bytes, str, int]:
    target = resolve_workspace_file_path(workspace_id, file_path)
    size_bytes = target.stat().st_size
    if size_bytes > _MAX_RAW_FILE_BYTES:
        raise WorkspaceFileError("file exceeds 16MB raw download limit")
    return target.read_bytes(), workspace_file_media_type(file_path), size_bytes


def write_workspace_file(
    workspace_id: str,
    file_path: str,
    content: str,
    *,
    base_sha256: str | None = None,
) -> dict[str, object]:
    root = resolve_workspace_root(workspace_id)
    target = _safe_resolve(root, file_path)
    if base_sha256 and target.is_file():
        try:
            on_disk = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            on_disk = None
        if on_disk is not None and _content_sha256(on_disk) != base_sha256:
            raise WorkspaceFileConflictError(
                f"{file_path} was changed on disk since it was loaded — reload before saving"
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "workspace_id": workspace_id,
        "path": file_path,
        "size_bytes": target.stat().st_size,
        "saved": True,
        "content_sha256": _content_sha256(content),
    }


def rename_workspace_file(
    workspace_id: str,
    old_path: str,
    new_path: str,
) -> dict[str, object]:
    root = resolve_workspace_root(workspace_id)
    source = _safe_resolve(root, old_path)
    target = _safe_resolve(root, new_path)

    if not source.is_file():
        raise WorkspaceFileError(f"file not found: {old_path}")

    if source == target:
        return {
            "workspace_id": workspace_id,
            "old_path": old_path,
            "path": new_path,
            "size_bytes": source.stat().st_size,
            "renamed": True,
        }

    if target.exists():
        raise WorkspaceFileError(f"file already exists: {new_path}")

    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    return {
        "workspace_id": workspace_id,
        "old_path": old_path,
        "path": new_path,
        "size_bytes": target.stat().st_size,
        "renamed": True,
    }
