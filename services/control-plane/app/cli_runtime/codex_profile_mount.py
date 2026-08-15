"""Validate and mount an isolated Codex credential inside Bubblewrap."""

from __future__ import annotations

from pathlib import Path


def resolve_codex_auth_path(raw_path: str, *, workspace: Path) -> Path | None:
    if not raw_path:
        return None
    try:
        candidate = Path(raw_path).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValueError("Codex profile auth file does not exist.") from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise ValueError("Codex profile auth must be a regular file.")
    if candidate == workspace or workspace in candidate.parents or candidate in workspace.parents:
        raise ValueError("Codex profile auth cannot overlap the workspace.")
    return candidate


def append_codex_auth_mount(arguments: list[str], source: Path | None, destination: Path) -> None:
    if source is not None:
        arguments.extend(["--ro-bind", str(source), str(destination)])
