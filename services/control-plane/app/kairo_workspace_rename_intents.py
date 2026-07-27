"""VAXON workspace rename intents (display name only; id stays stable)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.kairo_participant_memory import apply_participant_address
from app.kairo_workspace_intents import infer_workspace_id_from_content
from app.kairo_workspace_register_intents import (
    _SCHOOL_WORKSPACE_ID,
    resolve_known_purpose_workspace_id,
)
from app.workspace_project_bindings import (
    WorkspaceBindingError,
    get_workspace_project_binding,
    upsert_workspace_project_binding,
)

_RENAME_RE = re.compile(
    r"\b(?:change|rename|update)\b.{0,40}\b(?:name|workspace|title|label)\b.{0,40}\bto\b"
    r"|\b(?:call\s+it|rename\s+(?:it|this|the\s+workspace))\b.{0,40}\bto\b"
    r"|\bnew\s+name\b.{0,20}\b(?:is|=|:)\b",
    re.IGNORECASE | re.DOTALL,
)
_NEW_NAME_PATTERNS = (
    re.compile(
        r"\b(?:change|rename|update)\b.{0,40}\b(?:name|workspace|title|label)\b.{0,40}\bto\b\s+"
        r"[\"']?([A-Za-z0-9][A-Za-z0-9 ._+-]{1,64})",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:call\s+it|rename\s+(?:it|this|the\s+workspace))\b.{0,40}\bto\b\s+"
        r"[\"']?([A-Za-z0-9][A-Za-z0-9 ._+-]{1,64})",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bnew\s+name\b.{0,20}(?:is|=|:)\s*[\"']?([A-Za-z0-9][A-Za-z0-9 ._+-]{1,64})",
        re.IGNORECASE,
    ),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def is_rename_workspace_utterance(content: str) -> bool:
    return bool(_RENAME_RE.search(content.strip()))


def is_workspace_fleet_exempt_utterance(content: str) -> bool:
    from app.kairo_workspace_register_intents import is_register_workspace_utterance

    return is_rename_workspace_utterance(content) or is_register_workspace_utterance(content)


def is_workspace_fleet_exempt_utterance(content: str) -> bool:
    from app.kairo_workspace_register_intents import is_register_workspace_utterance

    return is_rename_workspace_utterance(content) or is_register_workspace_utterance(content)


def extract_rename_display_name(content: str) -> str | None:
    text = content.strip()
    for pattern in _NEW_NAME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1).strip(" \"'.,;:!?")
        candidate = re.split(r"\s+[-–—]\s+|\s+please\b|\s+and\b|\s+for\b", candidate, maxsplit=1)[
            0
        ].strip()
        if len(candidate) >= 2:
            return candidate
    return None


def resolve_rename_target_workspace_id(
    content: str,
    *,
    workspace_id: str | None,
) -> str | None:
    inferred = infer_workspace_id_from_content(content)
    if inferred:
        return inferred
    purpose = resolve_known_purpose_workspace_id(content)
    if purpose:
        return purpose
    current = (workspace_id or "").strip()
    if current and current.startswith("workspace_"):
        return current
    # Default rename target after Edu Pro / school assign work.
    if get_workspace_project_binding(_SCHOOL_WORKSPACE_ID) is not None:
        return _SCHOOL_WORKSPACE_ID
    return None


def _update_agents_company_name(workspace_id: str, display_name: str) -> None:
    path = _repo_root() / "config" / "workspace-agents.json"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    # Surgical replace inside the target company block only.
    block_re = re.compile(
        rf'("{re.escape(workspace_id)}"\s*:\s*\{{.*?"company_name"\s*:\s*")([^"]*)(")',
        re.DOTALL,
    )
    match = block_re.search(text)
    if not match:
        return
    updated = text[: match.start(2)] + display_name + text[match.end(2) :]
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _update_frontend_canonical_label(workspace_id: str, display_name: str) -> None:
    path = (
        _repo_root()
        / "apps"
        / "console-web"
        / "src"
        / "lib"
        / "kairo-entity-labels.ts"
    )
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    pattern = re.compile(
        rf"({re.escape(workspace_id)}:\s*)'([^']*)'",
    )
    if not pattern.search(text):
        return
    updated = pattern.sub(rf"\1'{display_name}'", text, count=1)
    # Ensure EDP Excellence alias exists for school renames.
    if workspace_id == _SCHOOL_WORKSPACE_ID and "edp excellence" not in updated.lower():
        updated = updated.replace(
            "  preschool: 'workspace_edudashpro_school',",
            "  preschool: 'workspace_edudashpro_school',\n"
            "  'edp excellence': 'workspace_edudashpro_school',\n"
            "  edpexcellence: 'workspace_edudashpro_school',",
            1,
        )
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def maybe_handle_rename_workspace_intent(
    *,
    content: str,
    workspace_id: str | None,
    guest_name: str | None,
) -> dict[str, Any] | None:
    trimmed = content.strip()
    if not trimmed or not is_rename_workspace_utterance(trimmed):
        return None

    new_name = extract_rename_display_name(trimmed)
    if not new_name:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                "I can rename a workspace — tell me the new name "
                "(for example: change the name to EDP Excellence).",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    target_id = resolve_rename_target_workspace_id(trimmed, workspace_id=workspace_id)
    if not target_id:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"I heard the new name **{new_name}**, but I need a target workspace.",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    binding = get_workspace_project_binding(target_id)
    if binding is None:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"`{target_id}` isn't bound yet, so I can't rename it to **{new_name}**.",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    old_name = binding.display_name or target_id
    try:
        updated = upsert_workspace_project_binding(
            workspace_id=target_id,
            project_root=str(binding.project_root),
            display_name=new_name,
        )
        _update_agents_company_name(target_id, new_name)
        _update_frontend_canonical_label(target_id, new_name)
    except (OSError, WorkspaceBindingError) as exc:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"I couldn't rename {old_name}: {exc}",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    return {
        "turn_kind": "action",
        "reply": apply_participant_address(
            f"Done — renamed **{old_name}** to **{new_name}** "
            f"(`{target_id}`). Opening it now.",
            guest_name,
        ),
        "source": "template",
        "command_content": None,
        "action": {"type": "switch_workspace", "workspace_id": target_id},
        "artifacts": [
            {
                "artifact_id": f"workspace-rename:{target_id}",
                "title": new_name,
                "summary": f"Renamed from {old_name}",
                "body": (
                    f"workspace_id={target_id}\n"
                    f"old_display_name={old_name}\n"
                    f"new_display_name={updated.display_name}\n"
                    f"project_root={updated.project_root}"
                ),
                "sources": [{"label": "bindings", "detail": "workspace-project-bindings.json"}],
                "actions": [
                    {
                        "label": "Open workspace",
                        "ui_action": {
                            "type": "switch_workspace",
                            "workspace_id": target_id,
                        },
                    }
                ],
            }
        ],
        "action_tier": "reversible_auto",
    }
