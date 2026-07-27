"""Fleet workspace assign/register intents for VAXON conversation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.kairo_participant_memory import apply_participant_address
from app.kairo_workspace_intents import infer_workspace_id_from_content, normalize_workspace_alias
from app.workspace_project_bindings import (
    WorkspaceBindingError,
    get_workspace_project_binding,
    upsert_workspace_project_binding,
)

# Prefer the existing school workspace for Edu Pro / aftercare / preschool asks.
_SCHOOL_WORKSPACE_ID = "workspace_edudashpro_school"
_KNOWN_PURPOSE_ALIASES: dict[str, str] = {
    "edu pro": _SCHOOL_WORKSPACE_ID,
    "edupro": _SCHOOL_WORKSPACE_ID,
    "edu-pro": _SCHOOL_WORKSPACE_ID,
    "edudash pro": _SCHOOL_WORKSPACE_ID,
    "edudashpro": _SCHOOL_WORKSPACE_ID,
    "edu dash pro": _SCHOOL_WORKSPACE_ID,
    "school of excellence": _SCHOOL_WORKSPACE_ID,
    "edudash pro school of excellence": _SCHOOL_WORKSPACE_ID,
    "edudashpro school of excellence": _SCHOOL_WORKSPACE_ID,
    "aftercare": _SCHOOL_WORKSPACE_ID,
    "preschool": _SCHOOL_WORKSPACE_ID,
    "edp excellence": _SCHOOL_WORKSPACE_ID,
    "edpexcellence": _SCHOOL_WORKSPACE_ID,
}

_ADD_WORKSPACE_RE = re.compile(
    r"\b(?:add|create|register|bind|set\s*up|spin\s*up|use|assign)\b.{0,100}\b(?:new\s+)?workspace\b"
    r"|\bnew\s+workspace\b"
    r"|\bconvert\b.{0,100}\bworkspace\b.{0,60}\bto\b"
    r"|\b(?:edu\s*pro|aftercare|preschool|school of excellence)\b",
    re.IGNORECASE | re.DOTALL,
)
_NAME_PATTERNS = (
    re.compile(
        r"\b(?:new\s+)?workspace\s+(?:named|called)\s+[\"']?([A-Za-z0-9][A-Za-z0-9 ._-]{1,64})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:new\s+)?workspace\s+[\"']?([A-Za-z][A-Za-z0-9 ._-]{1,64})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bto\s+[\"']?([A-Za-z][A-Za-z0-9 ._-]{1,64})\s+workspace\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:edu\s*pro|edudash\s*pro(?:\s+school(?:\s+of\s+excellence)?)?|"
        r"school\s+of\s+excellence|aftercare)\b",
        re.IGNORECASE,
    ),
)
_PATH_RE = re.compile(
    r"(?:project[_ ]root|path|at|under)\s*[:=]?\s*[\"']?(/[^\s\"']+)",
    re.IGNORECASE,
)
_SYNC_RE = re.compile(
    r"\b(?:in\s+sync|synced|sync|mirror|parity|paired|tied)\b.{0,40}\bwith\b\s+"
    r"([A-Za-z0-9][A-Za-z0-9 ._-]{1,40})",
    re.IGNORECASE,
)
_STOPWORDS = {
    "that",
    "this",
    "the",
    "a",
    "an",
    "new",
    "for",
    "with",
    "and",
    "least",
    "used",
    "please",
}


def is_register_workspace_utterance(content: str) -> bool:
    return bool(_ADD_WORKSPACE_RE.search(content.strip()))


def workspace_id_from_display_name(display_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", display_name.strip().lower()).strip("_")
    if not slug:
        raise WorkspaceBindingError("workspace display name is empty")
    return f"workspace_{slug}"


def resolve_known_purpose_workspace_id(phrase: str) -> str | None:
    normalized = normalize_workspace_alias(phrase)
    if not normalized:
        return None
    # Longest alias wins.
    matches = [
        (alias, workspace_id)
        for alias, workspace_id in _KNOWN_PURPOSE_ALIASES.items()
        if alias in normalized
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: len(item[0]), reverse=True)
    return matches[0][1]


def extract_workspace_display_name(content: str) -> str | None:
    text = content.strip()
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if pattern.groups == 0:
            candidate = match.group(0)
        else:
            candidate = match.group(1)
        candidate = candidate.strip(" \"'.,;:!?")
        candidate = re.split(r"\s+[-–—]\s+|\s+that\b|\s+which\b|\s+for\b", candidate, maxsplit=1)[
            0
        ].strip()
        normalized = normalize_workspace_alias(candidate)
        if not normalized or normalized in _STOPWORDS:
            continue
        if normalized in {"workspace", "workspaces"}:
            continue
        return candidate
    return None


def extract_project_root(content: str) -> str | None:
    match = _PATH_RE.search(content)
    return match.group(1).strip() if match else None


def extract_sync_peer_workspace_id(content: str) -> str | None:
    """Resolve the product-app peer to stay literate with.

    "EduDash Pro" / DashPro in a sync phrase means the product app
    (`workspace_dashpro`), never the School of Excellence workspace.
    """
    lower = content.lower()
    if re.search(
        r"\b(?:in\s+sync|synced|sync|mirror|parity|paired|tied)\b.{0,60}"
        r"\b(?:edu\s*dash\s*pro|edudash\s*pro|edudashpro|dash\s*pro|dashpro)\b",
        lower,
        re.DOTALL,
    ):
        return "workspace_dashpro"
    match = _SYNC_RE.search(content)
    if match:
        peer = infer_workspace_id_from_content(f"{match.group(1)} workspace")
        if peer == _SCHOOL_WORKSPACE_ID:
            return "workspace_dashpro"
        if peer:
            return peer
    if "dashpro" in lower or "dash pro" in lower:
        return "workspace_dashpro"
    return None


def _school_pair_note_body(*, sync_peer: str) -> str:
    return (
        "# VAXON workspace pairing\n\n"
        "## Workspace\n\n"
        "EduDash PRO School of Excellence — Preschool + Aftercare centre planning.\n\n"
        "## Focus\n\n"
        "- Primary: Aftercare programme for **Grade 1–7** learners\n"
        "- Later: extend school-age care to **Grade 8–12**\n"
        "- Also in scope: Preschool / ECD cohorts under the same centre brand\n\n"
        "## In sync with EduDash Pro\n\n"
        '"In sync" means this workspace must **understand the EduDash Pro app** '
        "(parent touchpoints, product surfaces, linkage notes) so centre ops "
        "align with the product.\n"
        "It does **not** mean rebuilding or editing the DashPro product repo "
        "from this tree.\n\n"
        f"Product app workspace: `{sync_peer}` "
        "(typically `/home/edp/Projectx/product/dashpro` when bound as DashPro).\n"
    )


def _pair_note(
    path: Path,
    *,
    sync_peer: str | None,
    workspace_id: str | None = None,
) -> None:
    if not sync_peer:
        return
    note = path / "VAXON_WORKSPACE_PAIRING.md"
    if workspace_id == _SCHOOL_WORKSPACE_ID:
        note.write_text(_school_pair_note_body(sync_peer=sync_peer), encoding="utf-8")
        return
    if note.exists():
        return
    note.write_text(
        "# VAXON workspace pairing\n\n"
        f"This workspace is paired with `{sync_peer}`.\n"
        "Stay literate with the linked EduDash Pro / DashPro app surfaces; "
        "do not rebuild the product here.\n",
        encoding="utf-8",
    )


def _switch_action(workspace_id: str) -> dict[str, str]:
    return {"type": "switch_workspace", "workspace_id": workspace_id}


def maybe_handle_register_workspace_intent(
    *,
    content: str,
    guest_name: str | None,
) -> dict[str, Any] | None:
    trimmed = content.strip()
    if not trimmed or not is_register_workspace_utterance(trimmed):
        return None

    display_name = extract_workspace_display_name(trimmed)
    sync_peer = extract_sync_peer_workspace_id(trimmed) or "workspace_dashpro"

    # Prefer known Edu Pro / aftercare → School of Excellence.
    purpose_id = resolve_known_purpose_workspace_id(display_name or trimmed)
    if purpose_id:
        binding = get_workspace_project_binding(purpose_id)
        if binding is None:
            return {
                "turn_kind": "action",
                "reply": apply_participant_address(
                    f"I know `{purpose_id}` should cover EduDash Pro Preschool + Aftercare, "
                    "but it isn't bound on disk yet.",
                    guest_name,
                ),
                "source": "template",
                "command_content": None,
                "action": None,
                "artifacts": [],
                "action_tier": "reversible_auto",
            }
        label = binding.display_name or purpose_id
        try:
            _pair_note(
                binding.project_root,
                sync_peer=sync_peer,
                workspace_id=purpose_id,
            )
        except OSError:
            pass
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"Using **{label}** (`{purpose_id}`) for EduDash Pro Preschool + Aftercare. "
                "Primary focus: aftercare for Grade 1–7 (Grade 8–12 later). "
                f"Stay literate with the EduDash Pro app via `{sync_peer}` — "
                "we don't rebuild the product here. Opening that workspace now.",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": _switch_action(purpose_id),
            "artifacts": [
                {
                    "artifact_id": f"workspace-assign:{purpose_id}",
                    "title": label,
                    "summary": (
                        "Preschool + Aftercare; focus Grade 1–7 aftercare; "
                        f"app literacy via {sync_peer}"
                    ),
                    "body": (
                        f"workspace_id={purpose_id}\n"
                        f"project_root={binding.project_root}\n"
                        f"sync_peer={sync_peer}\n"
                        "focus=aftercare_grade_1_7\n"
                        "later=aftercare_grade_8_12\n"
                        "also=preschool"
                    ),
                    "sources": [{"label": "bindings", "detail": "workspace-project-bindings.json"}],
                    "actions": [
                        {
                            "label": "Open workspace",
                            "ui_action": _switch_action(purpose_id),
                        }
                    ],
                }
            ],
            "action_tier": "reversible_auto",
        }

    if not display_name:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                "I can assign or register a workspace — name it "
                "(for example: use EduDash Pro School of Excellence for aftercare).",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": None,
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    # Existing binding by inferred id/name, else create a new binding.
    workspace_id = workspace_id_from_display_name(display_name)
    existing = get_workspace_project_binding(workspace_id)
    if existing is not None:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"{display_name} is already registered as `{workspace_id}`. Opening it now.",
                guest_name,
            ),
            "source": "template",
            "command_content": None,
            "action": _switch_action(workspace_id),
            "artifacts": [],
            "action_tier": "reversible_auto",
        }

    explicit_root = extract_project_root(trimmed)
    slug = workspace_id.removeprefix("workspace_")
    try:
        if explicit_root:
            project_root = Path(explicit_root).expanduser().resolve()
            project_root.mkdir(parents=True, exist_ok=True)
        else:
            project_root = (Path.home() / "Projectx" / "product" / slug).resolve()
            project_root.mkdir(parents=True, exist_ok=True)
            readme = project_root / "README.md"
            if not readme.exists():
                readme.write_text(
                    f"# {display_name}\n\nRegistered by VAXON.\n",
                    encoding="utf-8",
                )
        binding = upsert_workspace_project_binding(
            workspace_id=workspace_id,
            project_root=str(project_root),
            display_name=display_name,
        )
        _pair_note(
            binding.project_root,
            sync_peer=sync_peer,
            workspace_id=binding.workspace_id,
        )
    except (OSError, WorkspaceBindingError) as exc:
        return {
            "turn_kind": "action",
            "reply": apply_participant_address(
                f"I couldn't register {display_name}: {exc}",
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
            f"Registered **{display_name}** as `{binding.workspace_id}` "
            f"at `{binding.project_root}` and paired it with `{sync_peer}`.",
            guest_name,
        ),
        "source": "template",
        "command_content": None,
        "action": _switch_action(binding.workspace_id),
        "artifacts": [],
        "action_tier": "reversible_auto",
    }
