"""Map workspace identifiers to real on-disk project roots."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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
    defaults = [
        repo_root.resolve(),
        repo_root.parent.resolve(),
        Path.home().resolve(),
    ]
    parts = repo_root.resolve().parts
    if len(parts) >= 4 and parts[:3] == ("/", "run", "media"):
        defaults.append(Path(*parts[:4]).resolve())
    return tuple(dict.fromkeys(defaults))


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

        # Bindings are operator-maintained and project folders can be moved or
        # archived. One stale optional workspace must not make `/api/workspaces`
        # fail and leave the whole console in an unusable empty-shell state.
        try:
            project_root = _resolve_project_root(
                str(entry.get("project_root", "")), bindings_file=path
            )
        except WorkspaceBindingError as exc:
            # Missing folders are stale operational data; an out-of-allowlist
            # root is a security configuration error and must still fail closed.
            if "does not exist:" in str(exc):
                continue
            raise
        display_name = str(entry.get("display_name", "")).strip() or None
        bindings[normalized_id] = WorkspaceProjectBinding(
            workspace_id=normalized_id,
            project_root=project_root,
            display_name=display_name,
        )

    return bindings


def _read_bindings_entries(bindings_file: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """Parse the raw bindings JSON without resolving any single entry.

    Split out of load_workspace_project_bindings so a single-workspace lookup
    (get_workspace_project_binding) never has to materialize every other
    workspace's binding just to reach its own -- which is what made an
    unrelated misconfigured workspace (one whose project_root moved outside
    the allowlist) break get_workspace_record, and therefore effectively every
    feature that resolves a workspace, for every *other* workspace too.
    """
    path = bindings_file or default_bindings_file()
    if not path.is_file():
        return path, {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceBindingError(f"unable to read bindings file: {path}") from exc
    entries = payload.get("bindings")
    if not isinstance(entries, dict):
        raise WorkspaceBindingError("bindings file must contain a bindings object")
    return path, entries


def get_workspace_project_binding(workspace_id: str) -> WorkspaceProjectBinding | None:
    """Resolve exactly one workspace's binding, ignoring every other entry.

    Still fails closed (raises) if *this* workspace's own project_root sits
    outside the allowlist -- the security contract load_workspace_project_bindings
    enforces is preserved for the entry actually being asked about. It simply
    never touches, validates, or can be broken by any other workspace's entry.
    """
    normalized_id = workspace_id.strip()
    if not normalized_id:
        return None
    path, entries = _read_bindings_entries()
    entry = entries.get(normalized_id)
    if not isinstance(entry, dict):
        return None
    try:
        project_root = _resolve_project_root(str(entry.get("project_root", "")), bindings_file=path)
    except WorkspaceBindingError as exc:
        if "does not exist:" in str(exc):
            return None
        raise
    display_name = str(entry.get("display_name", "")).strip() or None
    return WorkspaceProjectBinding(
        workspace_id=normalized_id,
        project_root=project_root,
        display_name=display_name,
    )


def _normalize_workspace_id(workspace_id: str) -> str:
    normalized = workspace_id.strip()
    if not normalized:
        raise WorkspaceBindingError("workspace_id is required")
    if any(ch.isspace() for ch in normalized):
        raise WorkspaceBindingError("workspace_id must not contain whitespace")
    if not all(ch.isalnum() or ch in ("_", "-", ".") for ch in normalized):
        raise WorkspaceBindingError(
            "workspace_id may only contain letters, numbers, '_', '-', and '.'",
        )
    return normalized


def upsert_workspace_project_binding(
    *,
    workspace_id: str,
    project_root: str,
    display_name: str | None = None,
    bindings_file: Path | None = None,
) -> WorkspaceProjectBinding:
    """Persist a project-bound workspace into the bindings JSON file."""
    path = bindings_file or default_bindings_file()
    normalized_id = _normalize_workspace_id(workspace_id)
    resolved_root = _resolve_project_root(project_root, bindings_file=path)
    label = (display_name or "").strip() or None

    payload: dict[str, object] = {"bindings": {}}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceBindingError(f"unable to read bindings file: {path}") from exc
        if not isinstance(loaded, dict):
            raise WorkspaceBindingError("bindings file must contain a JSON object")
        entries = loaded.get("bindings", {})
        if entries is None:
            entries = {}
        if not isinstance(entries, dict):
            raise WorkspaceBindingError("bindings file must contain a bindings object")
        payload = {"bindings": dict(entries)}

    bindings = payload["bindings"]
    assert isinstance(bindings, dict)
    entry: dict[str, str] = {"project_root": str(resolved_root)}
    if label:
        entry["display_name"] = label
    bindings[normalized_id] = entry

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)

    binding = WorkspaceProjectBinding(
        workspace_id=normalized_id,
        project_root=resolved_root,
        display_name=label,
    )
    try:
        from app.workspace_agents.workspace_runtime_bootstrap import provision_workspace_runtime

        provision_workspace_runtime(
            normalized_id,
            project_root=resolved_root,
            display_name=label,
        )
    except Exception as exc:  # noqa: BLE001 — binding must succeed even if bootstrap fails
        logger.warning("workspace runtime bootstrap deferred for %s: %s", normalized_id, exc)
    return binding
