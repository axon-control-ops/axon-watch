"""List, read, and write UTF-8 files under workspace-scoped directories."""

from __future__ import annotations

from pathlib import Path

from app.terminal.workspace_roots import resolve_workspace_root
from app.workspace_catalog import get_workspace_record


class WorkspaceFileError(ValueError):
    pass


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


def list_workspace_files(workspace_id: str) -> list[dict[str, object]]:
    root = ensure_bootstrap_files(workspace_id)
    items: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".") or "/." in relative:
            continue
        items.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
            }
        )
    return items


def read_workspace_file(workspace_id: str, file_path: str) -> dict[str, object]:
    root = resolve_workspace_root(workspace_id)
    target = _safe_resolve(root, file_path)
    if not target.is_file():
        raise WorkspaceFileError(f"file not found: {file_path}")
    content = target.read_text(encoding="utf-8")
    return {
        "workspace_id": workspace_id,
        "path": file_path,
        "content": content,
        "size_bytes": target.stat().st_size,
    }


def write_workspace_file(workspace_id: str, file_path: str, content: str) -> dict[str, object]:
    root = resolve_workspace_root(workspace_id)
    target = _safe_resolve(root, file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "workspace_id": workspace_id,
        "path": file_path,
        "size_bytes": target.stat().st_size,
        "saved": True,
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
