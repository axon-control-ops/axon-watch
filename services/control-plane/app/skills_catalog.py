"""Discover agent skills from bound workspace project roots."""

from __future__ import annotations

import re

from app.workspace_project_bindings import list_valid_workspace_project_bindings

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
_DESC_RE = re.compile(r"^description:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)


def _parse_skill_frontmatter(text: str) -> tuple[str | None, str | None]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, None
    block = match.group(1)
    name_match = _NAME_RE.search(block)
    desc_match = _DESC_RE.search(block)
    name = name_match.group(1).strip() if name_match else None
    description = desc_match.group(1).strip() if desc_match else None
    return name, description


def list_workspace_skills() -> list[dict[str, str]]:
    bindings = list_valid_workspace_project_bindings()
    skills: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for binding in bindings.values():
        skills_root = binding.project_root / ".github" / "skills"
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            key = (binding.workspace_id, skill_dir.name)
            if key in seen:
                continue
            seen.add(key)
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            name, description = _parse_skill_frontmatter(text)
            relative = skill_file.relative_to(binding.project_root).as_posix()
            skills.append(
                {
                    "id": f"{binding.workspace_id}:{skill_dir.name}",
                    "name": name or skill_dir.name,
                    "description": description or "",
                    "workspace_id": binding.workspace_id,
                    "workspace_label": binding.display_name or binding.workspace_id,
                    "path": relative,
                    "slug": skill_dir.name,
                }
            )

    skills.sort(key=lambda item: (item["workspace_label"].lower(), item["name"].lower()))
    return skills


def build_skills_snapshot() -> dict[str, object]:
    items = list_workspace_skills()
    return {
        "items": items,
        "count": len(items),
        "workspaces_scanned": len(list_valid_workspace_project_bindings()),
    }
