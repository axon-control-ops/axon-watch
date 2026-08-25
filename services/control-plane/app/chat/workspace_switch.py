"""Resolve operator prompts that request switching the active workspace."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record
from app.workspace_files import WorkspaceFileError, list_workspace_files
from app.workspace_project_bindings import list_valid_workspace_project_bindings


class WorkspaceSwitchError(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceSwitchIntent:
    target_workspace_id: str
    display_name: str
    open_file_path: str | None = None


_SWITCH_VERBS = (
    "switch to",
    "change to",
    "go to",
    "open and switch to",
)


def _normalize_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _workspace_aliases(workspace_id: str, display_name: str | None) -> set[str]:
    aliases = {_normalize_alias(workspace_id.replace("workspace_", ""))}
    if display_name:
        aliases.add(_normalize_alias(display_name))
    if workspace_id == "workspace_dashpro":
        aliases.update({"dashpro", "dash pro"})
    if workspace_id == "workspace_axon_watch":
        aliases.update({"axon watch", "axon-watch", "axon x", "axon x watch"})
    return {alias for alias in aliases if alias}


def _looks_like_workspace_switch(content: str) -> bool:
    text = content.strip().lower()
    if not text:
        return False
    if not any(verb in text for verb in _SWITCH_VERBS):
        return False
    normalized = _normalize_alias(content)
    return "workspace" in text or any(
        alias in normalized
        for binding in list_valid_workspace_project_bindings().values()
        for alias in _workspace_aliases(binding.workspace_id, binding.display_name)
    )


def _match_target_workspace(content: str) -> tuple[str, str] | None:
    normalized = _normalize_alias(content)
    bindings = list_valid_workspace_project_bindings()
    matches: list[tuple[str, str, str]] = []

    for binding in bindings.values():
        display_name = binding.display_name or binding.workspace_id
        for alias in _workspace_aliases(binding.workspace_id, binding.display_name):
            if alias and alias in normalized:
                matches.append((binding.workspace_id, display_name, alias))

    if not matches:
        return None

    matches.sort(key=lambda item: len(item[2]), reverse=True)
    workspace_id, display_name, _ = matches[0]
    return workspace_id, display_name


def _preferred_open_file(workspace_id: str) -> str | None:
    try:
        files = list_workspace_files(workspace_id)
    except (WorkspaceFileError, OSError):
        return None
    for item in files:
        if item.get("path") == "README.md":
            return "README.md"
    return str(files[0]["path"]) if files else None


def resolve_workspace_switch_intent(content: str) -> WorkspaceSwitchIntent | None:
    if not _looks_like_workspace_switch(content):
        return None

    matched = _match_target_workspace(content)
    if matched is None:
        return None

    target_workspace_id, display_name = matched
    try:
        get_workspace_record(target_workspace_id)
    except WorkspaceNotFoundError as exc:
        raise WorkspaceSwitchError(str(exc)) from exc

    return WorkspaceSwitchIntent(
        target_workspace_id=target_workspace_id,
        display_name=display_name,
        open_file_path=_preferred_open_file(target_workspace_id),
    )


def build_workspace_switch_reply(intent: WorkspaceSwitchIntent) -> str:
    record = get_workspace_record(intent.target_workspace_id)
    project_root = record.get("project_root", "").strip()
    lines = [
        f"Switching the console to **{intent.display_name}** (`{intent.target_workspace_id}`).",
    ]
    if project_root:
        lines.append(f"The explorer and terminal will use `{project_root}` once the switch applies.")
    if intent.open_file_path:
        lines.append(f"I will open `{intent.open_file_path}` after the switch.")
    return " ".join(lines)


def workspace_switch_ui_action(intent: WorkspaceSwitchIntent) -> dict[str, object]:
    payload: dict[str, object] = {
        "type": "switch_workspace",
        "workspace_id": intent.target_workspace_id,
    }
    if intent.open_file_path:
        payload["open_file_path"] = intent.open_file_path
    return payload
