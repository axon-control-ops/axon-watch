"""Map workspace identifiers to real on-disk project roots."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


class WorkspaceBindingError(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceProjectBinding:
    workspace_id: str
    project_root: Path
    display_name: str | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_bindings_file() -> Path:
    configured = os.environ.get("AXON_WATCH_WORKSPACE_BINDINGS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "workspace-project-bindings.json").resolve()


def project_root_allowlist() -> tuple[Path, ...]:
    raw = os.environ.get("AXON_WATCH_PROJECT_ROOT_ALLOWLIST", "").strip()
    if raw:
        roots = []
        for entry in raw.split(":"):
            text = entry.strip()
            if not text:
                continue
            path = Path(text).expanduser().resolve()
            roots.append(path)
        if roots:
            return tuple(roots)

    repo_root = _repo_root()
    return (
        repo_root.resolve(),
        repo_root.parent.resolve(),
        Path.home().resolve(),
    )


def _resolve_project_root(raw_root: str, *, bindings_file: Path) -> Path:
    text = raw_root.strip()
    if not text:
        raise WorkspaceBindingError("project_root is required")

    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (_repo_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.exists():
        raise WorkspaceBindingError(f"project_root does not exist: {candidate}")
    if not candidate.is_dir():
        raise WorkspaceBindingError(f"project_root is not a directory: {candidate}")

    for allowed in project_root_allowlist():
        try:
            candidate.relative_to(allowed)
            return candidate
        except ValueError:
            continue

    raise WorkspaceBindingError(
        f"project_root is outside allowlist: {candidate}",
    )


def load_workspace_project_bindings(
    bindings_file: Path | None = None,
) -> dict[str, WorkspaceProjectBinding]:
    path = bindings_file or default_bindings_file()
    if not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceBindingError(f"unable to read bindings file: {path}") from exc

    entries = payload.get("bindings")
    if not isinstance(entries, dict):
        raise WorkspaceBindingError("bindings file must contain a bindings object")

    bindings: dict[str, WorkspaceProjectBinding] = {}
    for workspace_id, entry in entries.items():
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            continue
        if not isinstance(entry, dict):
            raise WorkspaceBindingError(f"binding for {normalized_id} must be an object")

        project_root = _resolve_project_root(str(entry.get("project_root", "")), bindings_file=path)
        display_name = str(entry.get("display_name", "")).strip() or None
        bindings[normalized_id] = WorkspaceProjectBinding(
            workspace_id=normalized_id,
            project_root=project_root,
            display_name=display_name,
        )

    return bindings


def get_workspace_project_binding(workspace_id: str) -> WorkspaceProjectBinding | None:
    normalized_id = workspace_id.strip()
    if not normalized_id:
        return None
    return load_workspace_project_bindings().get(normalized_id)
