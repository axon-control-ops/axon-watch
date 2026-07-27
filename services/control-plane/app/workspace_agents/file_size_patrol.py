"""Scheduler-driven file-size hygiene patrol with safe autopilot outcomes."""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from app.persistence import task_store

logger = logging.getLogger(__name__)

MANIFEST_REL = "scripts/guardrails/hotspot_budgets.json"
PATROL_GOAL_PREFIX = "File-size patrol:"
DEFAULT_OWNER_ROLE = "watcher"
DEFAULT_MAX_NEW_TASKS = 1

PatrolKind = Literal["stale_manifest", "extraction"]


@dataclass(frozen=True)
class FileSizePatrolFinding:
    kind: PatrolKind
    path: str
    lines: int
    budget: int | None = None
    suggested_max_lines: int | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_guardrails_importable(root: Path) -> None:
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def classify_file_size_findings(root: Path | None = None) -> list[FileSizePatrolFinding]:
    """Scan tracked sources and classify stale-ratchet vs extraction work."""
    repo = root or _repo_root()
    _ensure_guardrails_importable(repo)
    from scripts.guardrails.common import (
        DEFAULT_LIMITS,
        evaluate_ratcheted_file,
        line_count,
        load_budget_manifest,
        ratcheted_entries,
        tracked_source_files,
    )

    manifest = load_budget_manifest(repo)
    ratchets = ratcheted_entries(manifest)
    findings: list[FileSizePatrolFinding] = []

    for path in tracked_source_files(repo):
        rel = path.relative_to(repo).as_posix()
        lines = line_count(path)
        ratchet = ratchets.get(rel)
        if ratchet:
            max_lines = int(ratchet["max_lines"])
            error = evaluate_ratcheted_file(rel, lines, max_lines)
            if not error:
                continue
            if lines <= max_lines:
                findings.append(
                    FileSizePatrolFinding(
                        kind="stale_manifest",
                        path=rel,
                        lines=lines,
                        budget=max_lines,
                        suggested_max_lines=lines,
                        detail=error,
                    )
                )
            else:
                findings.append(
                    FileSizePatrolFinding(
                        kind="extraction",
                        path=rel,
                        lines=lines,
                        budget=max_lines,
                        detail=error,
                    )
                )
            continue

        limits = DEFAULT_LIMITS.get(path.suffix.lower()) or {}
        hard_limit = int(limits.get("hard") or 0)
        if hard_limit and lines > hard_limit:
            findings.append(
                FileSizePatrolFinding(
                    kind="extraction",
                    path=rel,
                    lines=lines,
                    budget=hard_limit,
                    detail=(
                        f"{rel}: {lines} lines exceeds hard limit {hard_limit}; "
                        "extract or add a ratchet entry"
                    ),
                )
            )
    return findings


def propose_manifest_lowering(
    manifest: dict[str, Any],
    *,
    path: str,
    suggested_max_lines: int,
) -> dict[str, Any] | None:
    """Return a lowered manifest copy, or None when no safe lowering applies.

    Never raises a ratchet. Only lowers an existing entry's max_lines.
    """
    if suggested_max_lines <= 0:
        return None
    updated = {
        "critical_hotspots": dict(manifest.get("critical_hotspots") or {}),
        "ratcheted_oversize_files": dict(manifest.get("ratcheted_oversize_files") or {}),
    }
    for section in ("critical_hotspots", "ratcheted_oversize_files"):
        entry = updated[section].get(path)
        if not isinstance(entry, dict):
            continue
        current = int(entry.get("max_lines") or 0)
        if current <= suggested_max_lines:
            return None
        new_entry = dict(entry)
        new_entry["max_lines"] = int(suggested_max_lines)
        updated[section][path] = new_entry
        result = dict(manifest)
        result["critical_hotspots"] = updated["critical_hotspots"]
        result["ratcheted_oversize_files"] = updated["ratcheted_oversize_files"]
        return result
    return None


def _open_patrol_tasks(workspace_id: str) -> list[dict[str, Any]]:
    openish: list[dict[str, Any]] = []
    for status in ("open", "leased"):
        openish.extend(
            task_store.list_tasks(
                workspace_id=workspace_id,
                status=status,
                limit=200,
            )
        )
    return [
        row
        for row in openish
        if str(row.get("goal") or "").startswith(PATROL_GOAL_PREFIX)
    ]


def _already_tracked(path: str, existing: list[dict[str, Any]]) -> bool:
    needle = path.lower()
    for row in existing:
        goal = str(row.get("goal") or "").lower()
        allowed = row.get("allowed_paths") if isinstance(row.get("allowed_paths"), list) else []
        if needle in goal:
            return True
        if any(needle == str(item).strip().lower() for item in allowed):
            return True
    return False


def _build_task_payload(finding: FileSizePatrolFinding) -> dict[str, Any]:
    if finding.kind == "stale_manifest":
        target = finding.suggested_max_lines or finding.lines
        return {
            "goal": (
                f"{PATROL_GOAL_PREFIX} lower stale ratchet for `{finding.path}` "
                f"from {finding.budget} to {target} lines in `{MANIFEST_REL}` only."
            ),
            "acceptance_criteria": (
                f"Edit only `{MANIFEST_REL}` to set max_lines={target} for "
                f"`{finding.path}`. Never raise any ratchet. Open a draft PR; "
                "run `npm run verify:contracts` and report the Fast Gate watch URL."
            ),
            "allowed_paths": [MANIFEST_REL],
            "exclusive_paths": [MANIFEST_REL],
            "risk": "low",
        }
    return {
        "goal": (
            f"{PATROL_GOAL_PREFIX} extract/shrink `{finding.path}` "
            f"({finding.lines} lines; budget {finding.budget})."
        ),
        "acceptance_criteria": (
            f"Shrink `{finding.path}` below budget with a focused extraction. "
            "Keep the change bounded to the hotspot and its new helper module(s). "
            "Do not raise ratchets. Draft PR only; verify:contracts + targeted tests."
        ),
        "allowed_paths": [finding.path, str(Path(finding.path).parent.as_posix()) + "/"],
        "exclusive_paths": [finding.path],
        "risk": "normal",
    }


def enqueue_file_size_patrol_tasks(
    *,
    workspace_id: str,
    findings: list[FileSizePatrolFinding] | None = None,
    owner_role: str = DEFAULT_OWNER_ROLE,
    max_new_tasks: int = DEFAULT_MAX_NEW_TASKS,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Create bounded ledger tasks for classified file-size findings."""
    workspace = workspace_id.strip()
    if not workspace:
        return []
    classified = findings if findings is not None else classify_file_size_findings(root)
    if not classified:
        return []
    existing = _open_patrol_tasks(workspace)
    created: list[dict[str, Any]] = []
    # Prefer safe autopilot (stale manifest) before heavier extraction work.
    ordered = sorted(
        classified,
        key=lambda item: (0 if item.kind == "stale_manifest" else 1, item.path),
    )
    for finding in ordered:
        if len(created) >= max(1, int(max_new_tasks)):
            break
        if _already_tracked(finding.path, existing + created):
            continue
        payload = _build_task_payload(finding)
        try:
            record = task_store.create_task(
                workspace_id=workspace,
                goal=payload["goal"],
                acceptance_criteria=payload["acceptance_criteria"],
                risk=payload["risk"],
                owner_role=owner_role,
                allowed_paths=payload["allowed_paths"],
                exclusive_paths=payload["exclusive_paths"],
                attempt_budget=2,
            )
        except task_store.TaskLedgerError as exc:
            logger.warning("file-size patrol could not create task: %s", exc)
            continue
        created.append(record)
    return created


def run_file_size_patrol(
    *,
    workspace_id: str = "workspace_axon_watch",
    owner_role: str = DEFAULT_OWNER_ROLE,
    max_new_tasks: int = DEFAULT_MAX_NEW_TASKS,
    root: Path | None = None,
) -> dict[str, Any]:
    findings = classify_file_size_findings(root)
    created = enqueue_file_size_patrol_tasks(
        workspace_id=workspace_id,
        findings=findings,
        owner_role=owner_role,
        max_new_tasks=max_new_tasks,
        root=root,
    )
    return {
        "work_source": "file_size_patrol",
        "finding_count": len(findings),
        "stale_manifest_count": sum(1 for item in findings if item.kind == "stale_manifest"),
        "extraction_count": sum(1 for item in findings if item.kind == "extraction"),
        "created_tasks": created,
    }


__all__ = [
    "FileSizePatrolFinding",
    "MANIFEST_REL",
    "PATROL_GOAL_PREFIX",
    "classify_file_size_findings",
    "enqueue_file_size_patrol_tasks",
    "propose_manifest_lowering",
    "run_file_size_patrol",
]
