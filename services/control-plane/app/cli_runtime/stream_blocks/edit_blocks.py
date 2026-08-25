"""File edit transcript block helpers shared by local CLI runtime adapters."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path

from app.cli_runtime.stream_blocks.terminal_blocks import _relative_path

_DIFF_TIMEOUT_SECONDS = 8
_MAX_CREATED_FILE_BYTES = 96_000


@dataclass(frozen=True)
class EditBlock:
    path: str
    diff: str
    added: int
    removed: int


def diff_counts(diff: str) -> tuple[int, int]:
    added = sum(
        1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")
    )
    return added, removed


def render_edit_block(
    *,
    path: str,
    diff: str = "",
    added: int | None = None,
    removed: int | None = None,
) -> str:
    clean_path = str(path or "").strip() or "changed file"
    clean_diff = str(diff or "").strip()
    if added is None or removed is None:
        added, removed = diff_counts(clean_diff)
    return f"\n:::edit {clean_path} +{int(added or 0)} -{int(removed or 0)}\n{clean_diff}\n:::\n"


def edit_block_for_path(
    *,
    workspace_root: Path,
    path: str,
    diff: str = "",
) -> EditBlock | None:
    """Return a diff-backed edit block for ``path``.

    Runtime streams are inconsistent: Cursor usually sends a full diff, while
    Codex/Claude may only report that a path changed. When the diff is missing,
    derive it from the checkout so the UI still renders "Created file" /
    "Edited file" instead of a zero-line "Checked file" card.
    """
    root = workspace_root.expanduser().resolve() if workspace_root else Path.cwd().resolve()
    rel_path = _relative_path(str(path or ""), str(root)).strip()
    if not rel_path:
        return None
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    full_path = (root / rel).resolve()
    try:
        full_path.relative_to(root)
    except ValueError:
        return None

    clean_diff = str(diff or "").strip()
    had_explicit_diff = bool(clean_diff)
    if not clean_diff:
        clean_diff = _git_diff_for_path(root, rel_path)
        if not clean_diff and not _git_tracks_path(root, rel_path):
            clean_diff = _new_file_diff(full_path, rel_path)
    if not clean_diff and not had_explicit_diff:
        return None
    added, removed = diff_counts(clean_diff)
    return EditBlock(path=rel_path, diff=clean_diff, added=added, removed=removed)


def render_edit_block_for_path(
    *,
    workspace_root: Path,
    path: str,
    diff: str = "",
) -> str:
    block = edit_block_for_path(workspace_root=workspace_root, path=path, diff=diff)
    if block is None:
        return ""
    return render_edit_block(
        path=block.path,
        diff=block.diff,
        added=block.added,
        removed=block.removed,
    )


def _git_diff_for_path(root: Path, rel_path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=3", "--no-ext-diff", "HEAD", "--", rel_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=_DIFF_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip() if result.returncode in {0, 1} else ""


def _git_tracks_path(root: Path, rel_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=_DIFF_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    return result.returncode == 0


def _new_file_diff(path: Path, rel_path: str) -> str:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_CREATED_FILE_BYTES:
            return ""
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return "\n".join(
        unified_diff(
            [],
            text.splitlines(),
            fromfile="/dev/null",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
    ).strip()
