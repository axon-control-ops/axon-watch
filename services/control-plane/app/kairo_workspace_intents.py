"""Workspace mention parsing for KAIRO conversation."""

from __future__ import annotations

import re

from app.workspace_project_bindings import load_workspace_project_bindings


def normalize_workspace_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def workspace_aliases(workspace_id: str, display_name: str | None) -> set[str]:
    aliases = {normalize_workspace_alias(workspace_id.replace("workspace_", ""))}
    if display_name:
        aliases.add(normalize_workspace_alias(display_name))
    if workspace_id == "workspace_dashpro":
        aliases.update(
            {
                "dashpro",
                "dash pro",
                "best pro",
                "this pro",
                "probox space",
                "dashpro workspace",
            }
        )
    if workspace_id == "workspace_tps":
        aliases.update({"tps", "tps workspace", "tee pee ess"})
    if workspace_id == "workspace_young_eagles_day_care":
        aliases.update(
            {
                "young eagles",
                "young eagles day care",
                "young eagles daycare",
            }
        )
    if workspace_id == "workspace_edudashpro_school":
        aliases.update(
            {
                "edu pro",
                "edupro",
                "edu-pro",
                "edudash pro",
                "edudashpro",
                "edu dash pro",
                "school of excellence",
                "aftercare",
                "preschool",
                "edp excellence",
                "edpexcellence",
            }
        )
    return {alias for alias in aliases if alias}


def infer_workspace_id_from_content(content: str) -> str | None:
    normalized = normalize_workspace_alias(content)
    if not normalized:
        return None
    bindings = load_workspace_project_bindings()
    matches: list[tuple[str, str]] = []
    for binding in bindings.values():
        for alias in workspace_aliases(binding.workspace_id, binding.display_name):
            if alias and alias in normalized:
                matches.append((binding.workspace_id, alias))
    if matches:
        matches.sort(key=lambda item: len(item[1]), reverse=True)
        return matches[0][0]
    if "pro workspace" in normalized or "probox space" in normalized:
        return "workspace_dashpro"
    return None

