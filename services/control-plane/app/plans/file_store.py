"""Filesystem store for durable plan Markdown under `.axon/plans/`."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from app.plans.models import PlanRecord
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_PLAN_ID_RE = re.compile(r"^plan_[a-f0-9]{12}$")
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


class PlanStoreError(ValueError):
    pass


def plans_dir_for_workspace(workspace_id: str) -> Path:
    root = resolve_workspace_root(workspace_id)
    plans_dir = (root / ".axon" / "plans").resolve()
    if not str(plans_dir).startswith(str(root.resolve())):
        raise PlanStoreError("plans directory escapes workspace root")
    plans_dir.mkdir(parents=True, exist_ok=True)
    return plans_dir


def plan_file_path(workspace_id: str, plan_id: str) -> Path:
    plan_id = str(plan_id or "").strip()
    if not _PLAN_ID_RE.match(plan_id):
        raise PlanStoreError("invalid plan_id")
    plans_dir = plans_dir_for_workspace(workspace_id)
    path = (plans_dir / f"{plan_id}.md").resolve()
    if not str(path).startswith(str(plans_dir)):
        raise PlanStoreError("plan path escapes plans directory")
    return path


def _escape_yaml_string(value: str) -> str:
    return json.dumps(str(value or ""), ensure_ascii=False)


def render_plan_markdown(record: PlanRecord) -> str:
    frontmatter = "\n".join(
        [
            "---",
            f"plan_id: {_escape_yaml_string(record.plan_id)}",
            f"workspace_id: {_escape_yaml_string(record.workspace_id)}",
            f"thread_id: {_escape_yaml_string(record.thread_id)}",
            f"source_message_id: {_escape_yaml_string(record.source_message_id)}",
            f"title: {_escape_yaml_string(record.title)}",
            f"created_at: {_escape_yaml_string(record.created_at)}",
            f"updated_at: {_escape_yaml_string(record.updated_at)}",
            "---",
            "",
        ]
    )
    body = record.content.strip() + "\n"
    return frontmatter + body


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        meta[key] = value
    return meta, match.group(2).lstrip("\n")


def write_plan_file(record: PlanRecord) -> Path:
    path = plan_file_path(record.workspace_id, record.plan_id)
    payload = render_plan_markdown(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{record.plan_id}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path


def read_plan_file(workspace_id: str, plan_id: str) -> PlanRecord:
    path = plan_file_path(workspace_id, plan_id)
    if not path.is_file():
        raise PlanStoreError("plan not found")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlanStoreError(f"unable to read plan: {exc}") from exc
    meta, body = _parse_frontmatter(raw)
    if str(meta.get("workspace_id") or "").strip() not in {"", workspace_id}:
        raise PlanStoreError("plan workspace mismatch")
    return PlanRecord(
        plan_id=plan_id,
        workspace_id=workspace_id,
        thread_id=str(meta.get("thread_id") or ""),
        source_message_id=str(meta.get("source_message_id") or ""),
        title=str(meta.get("title") or plan_id),
        content=body.strip() + ("\n" if body.strip() else ""),
        path=str(path),
        created_at=str(meta.get("created_at") or ""),
        updated_at=str(meta.get("updated_at") or ""),
    )


def list_plan_files(workspace_id: str) -> list[PlanRecord]:
    try:
        plans_dir = plans_dir_for_workspace(workspace_id)
    except WorkspaceRootError as exc:
        raise PlanStoreError(str(exc)) from exc
    records: list[PlanRecord] = []
    for path in sorted(plans_dir.glob("plan_*.md"), key=lambda item: item.stat().st_mtime, reverse=True):
        plan_id = path.stem
        if not _PLAN_ID_RE.match(plan_id):
            continue
        try:
            records.append(read_plan_file(workspace_id, plan_id))
        except PlanStoreError:
            continue
    return records
