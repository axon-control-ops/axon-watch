"""Capture and query durable Plan-mode artifacts."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from app.plans.file_store import (
    PlanStoreError,
    list_plan_files,
    read_plan_file,
    write_plan_file,
)
from app.plans.models import PlanRecord
from app.terminal.workspace_roots import WorkspaceRootError

# Tool chips are single-line headers (no body). Do not swallow following prose.
_TOOL_FENCE_RE = re.compile(r"^:::tool\b.*$", re.MULTILINE)
_THINKING_FENCE_RE = re.compile(r"^:::thinking\n.*?^:::\s*$", re.MULTILINE | re.DOTALL)
_PLAN_FENCE_RE = re.compile(r"^:::plan\b.*(?:\n:::)?\s*$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
_NUMBERED_STEP_RE = re.compile(r"(?m)^\s*(?:\d+[\.\)]|\-\s+\[[ xX]\])\s+\S+")
_BULLET_RE = re.compile(r"(?m)^\s*[-*]\s+\S.{8,}")
_TODO_RE = re.compile(r"(?m)^\s*-\s+\[[ xX]\]\s+\S+")
_PROCESS_LINE_RE = re.compile(
    r"^(i'?ll|i will|i am|i'?m|let me|looking|gathering|drafting|searching|"
    r"checking|reading|i have enough|the request is|choice\s+\*?\*?\d)\b",
    re.IGNORECASE,
)
_WEAK_TITLE_RE = re.compile(
    r"^(i'?ll|i will|i am|i'?m|let me|looking|gathering|drafting|searching|"
    r"checking|reading|i have enough|the request)\b",
    re.IGNORECASE,
)


class PlanCaptureError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_plan_id() -> str:
    return f"plan_{secrets.token_hex(6)}"


def strip_noisy_fences(content: str) -> str:
    text = str(content or "")
    text = _THINKING_FENCE_RE.sub("", text)
    text = _TOOL_FENCE_RE.sub("", text)
    text = _PLAN_FENCE_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_weak_title(title: str) -> bool:
    trimmed = title.strip().lstrip("*").strip()
    if len(trimmed) < 4:
        return True
    if _WEAK_TITLE_RE.match(trimmed):
        return True
    lower = trimmed.lower()
    if lower.startswith("choice "):
        return True
    if any(
        marker in lower
        for marker in (
            "gathering the",
            "drafting that",
            "i'll check",
            "i will check",
            "so i can draft",
        )
    ):
        return True
    return False


def extract_plan_title(content: str) -> str:
    cleaned = strip_noisy_fences(content)
    for match in _HEADING_RE.finditer(cleaned):
        title = match.group(1).strip()
        if title and not _is_weak_title(title):
            return title[:120]
    for line in cleaned.splitlines():
        candidate = line.strip().lstrip("#").strip()
        if not candidate or _is_weak_title(candidate):
            continue
        if candidate.startswith(("*", "-", "1.", "2.", "3.")):
            continue
        return candidate[:120]
    return "Untitled plan"


def looks_like_clarifying_choice_prompt(text: str) -> bool:
    lower = text.lower()
    if "reply with" in lower and re.search(r"\b[123]\b", text):
        return True
    if "what should this plan focus" in lower:
        return True
    if re.search(r"(?m)^\s*1[\.\)]\s+.+\n\s*2[\.\)]\s+", text) and any(
        key in lower for key in ("reply with", "pick", "unless you pick", "what should")
    ):
        return True
    return False


def looks_like_process_narration(text: str) -> bool:
    lines = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith(":::")
    ]
    if not lines:
        return True
    substantive = [ln for ln in lines if not ln.startswith("#")]
    if not substantive:
        return True
    process = sum(1 for ln in substantive if _PROCESS_LINE_RE.match(ln))
    last = substantive[-1].lower()
    if any(
        last.startswith(prefix)
        for prefix in (
            "drafting",
            "gathering",
            "i'll look",
            "i'll search",
            "looking through",
            "i have enough",
        )
    ) and len(_NUMBERED_STEP_RE.findall(text)) < 3:
        return True
    return process >= max(2, (len(substantive) + 1) // 2)


def is_durable_plan_body(content: str) -> bool:
    """Fail closed: only persist replies that look like a finished plan artifact."""

    body = strip_noisy_fences(content)
    if len(body) < 180:
        return False
    if looks_like_clarifying_choice_prompt(body):
        return False
    if looks_like_process_narration(body):
        return False
    numbered = len(_NUMBERED_STEP_RE.findall(body))
    bullets = len(_BULLET_RE.findall(body))
    headings = len(_HEADING_RE.findall(body))
    todos = len(_TODO_RE.findall(body))
    if todos >= 3:
        return True
    if numbered >= 3:
        return True
    if numbered >= 2 and (bullets >= 2 or headings >= 2):
        return True
    if headings >= 2 and bullets >= 3:
        return True
    return False


def build_plan_transcript_fence(plan_id: str, title: str) -> str:
    safe_title = " ".join(str(title or "Untitled plan").split())
    return f":::plan {plan_id} {safe_title}\n:::"


def capture_plan_from_reply(
    *,
    workspace_id: str,
    thread_id: str,
    source_message_id: str,
    content: str,
    created_at: str | None = None,
) -> tuple[PlanRecord, str]:
    body = strip_noisy_fences(content)
    if not body:
        raise PlanCaptureError("plan content is empty")
    if not is_durable_plan_body(body):
        raise PlanCaptureError("reply is not a complete durable plan")
    stamp = created_at or _utc_now()
    title = extract_plan_title(body)
    stored_body = body if body.lstrip().startswith("#") else f"# {title}\n\n{body}"
    record = PlanRecord(
        plan_id=new_plan_id(),
        workspace_id=workspace_id.strip(),
        thread_id=thread_id.strip(),
        source_message_id=source_message_id.strip(),
        title=title,
        content=stored_body.strip() + "\n",
        path="",
        created_at=stamp,
        updated_at=stamp,
    )
    try:
        path = write_plan_file(record)
    except (PlanStoreError, WorkspaceRootError, OSError) as exc:
        raise PlanCaptureError(str(exc)) from exc
    record = PlanRecord(
        plan_id=record.plan_id,
        workspace_id=record.workspace_id,
        thread_id=record.thread_id,
        source_message_id=record.source_message_id,
        title=record.title,
        content=record.content,
        path=str(path),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
    return record, build_plan_transcript_fence(record.plan_id, record.title)


def get_plan(workspace_id: str, plan_id: str) -> PlanRecord:
    try:
        return read_plan_file(workspace_id, plan_id)
    except (PlanStoreError, WorkspaceRootError) as exc:
        raise PlanCaptureError(str(exc)) from exc


def list_plans(workspace_id: str) -> list[PlanRecord]:
    try:
        return list_plan_files(workspace_id)
    except (PlanStoreError, WorkspaceRootError) as exc:
        raise PlanCaptureError(str(exc)) from exc


def maybe_attach_plan_artifact(
    *,
    composer_mode: str,
    workspace_id: str,
    thread_id: str,
    source_message_id: str,
    agent_content: str,
    created_at: str | None = None,
) -> tuple[str, dict[str, object] | None]:
    """Capture a Plan-mode reply and append a durable :::plan fence.

    Failures are swallowed by the caller — returns original content on error.
    Incomplete / exploratory Plan-mode narration is intentionally not captured.
    """

    if str(composer_mode or "").strip().lower() != "plan":
        return agent_content, None
    try:
        record, fence = capture_plan_from_reply(
            workspace_id=workspace_id,
            thread_id=thread_id,
            source_message_id=source_message_id,
            content=agent_content,
            created_at=created_at,
        )
    except PlanCaptureError:
        return agent_content, None
    updated = str(agent_content or "").rstrip() + "\n\n" + fence + "\n"
    return updated, {
        "plan_id": record.plan_id,
        "title": record.title,
        "path": record.path,
    }
