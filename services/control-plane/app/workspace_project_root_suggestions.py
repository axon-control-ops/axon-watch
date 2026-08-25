"""Suggest candidate project_root paths for the Add Workspace form.

A new project almost always lands as a new sibling directory under a parent
that already hosts a registered project (e.g. projectx/client/, projectx/
product/, repos/axon-nvme/repos/) -- scanning those known parents instead of
the whole filesystem keeps this fast, predictable, and automatically bounded
by the same allowlist project_root registration already enforces, without
hardcoding any path specific to one deployment.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.workspace_project_bindings import (
    list_valid_workspace_project_bindings,
    project_root_allowlist,
)

_MAX_SUGGESTIONS = 8
_MAX_ENTRIES_PER_PARENT = 500
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return {token for token in _TOKEN_RE.findall(spaced.lower()) if len(token) >= 2}


def _is_within_allowlist(path: Path, allowlist: tuple[Path, ...]) -> bool:
    for allowed in allowlist:
        try:
            path.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


def _score(candidate_name: str, query_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    candidate_tokens = _tokens(candidate_name)
    if candidate_tokens:
        overlap = len(query_tokens & candidate_tokens)
        if overlap:
            return overlap / len(query_tokens)
    lowered = candidate_name.lower()
    if any(token in lowered for token in query_tokens):
        return 0.25
    return 0.0


def suggest_project_roots(query: str, *, limit: int = _MAX_SUGGESTIONS) -> list[dict[str, Any]]:
    """Rank sibling directories of already-registered projects against `query`.

    Empty query returns the same candidate set unranked (newest-looking first
    by directory name), so the form can still offer something before the
    operator has typed a workspace id.
    """
    bindings = list_valid_workspace_project_bindings()
    bound_roots = {str(binding.project_root) for binding in bindings.values()}
    known_parents = sorted({str(binding.project_root.parent) for binding in bindings.values()})
    allowlist = project_root_allowlist()
    query_tokens = _tokens(query)

    scored: list[tuple[float, dict[str, Any]]] = []
    seen: set[str] = set()
    for parent_str in known_parents:
        parent = Path(parent_str)
        if not parent.is_dir():
            continue
        try:
            entries = sorted(parent.iterdir(), key=lambda item: item.name.lower())
        except OSError:
            continue
        for entry in entries[:_MAX_ENTRIES_PER_PARENT]:
            if entry.name.startswith("."):
                continue
            try:
                if not entry.is_dir():
                    continue
                resolved = entry.resolve()
            except OSError:
                continue
            resolved_str = str(resolved)
            if resolved_str in bound_roots or resolved_str in seen:
                continue
            seen.add(resolved_str)
            if not _is_within_allowlist(resolved, allowlist):
                continue
            score = _score(entry.name, query_tokens)
            scored.append(
                (
                    score,
                    {
                        "project_root": resolved_str,
                        "label": entry.name,
                        "parent": parent_str,
                    },
                )
            )

    if query_tokens:
        scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1]["label"].lower()))
    return [candidate for _score_value, candidate in scored[:limit]]
