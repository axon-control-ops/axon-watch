"""Typed progress milestones for streamed agent turns."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.persistence import chat_store
from app.chat.stream_hub import publish_chat_stream_event

_RESEARCH_HEADER_RE = re.compile(r"^:::research\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class _ResearchBlock:
    query: str
    open: bool


def _parse_research_blocks(content: str) -> list[_ResearchBlock]:
    lines = content.splitlines()
    blocks: list[_ResearchBlock] = []
    index = 0
    while index < len(lines):
        match = _RESEARCH_HEADER_RE.match(lines[index])
        if not match:
            index += 1
            continue
        query = match.group(1).strip()
        index += 1
        closed = False
        while index < len(lines):
            if lines[index].rstrip() == ":::":
                closed = True
                index += 1
                break
            index += 1
        blocks.append(_ResearchBlock(query=query, open=not closed))
    return blocks


def research_milestones_for_delta(
    previous_content: str,
    content: str,
) -> list[dict[str, Any]]:
    previous_blocks = _parse_research_blocks(previous_content)
    current_blocks = _parse_research_blocks(content)
    milestones: list[dict[str, Any]] = []

    for index in range(len(previous_blocks), len(current_blocks)):
        block = current_blocks[index]
        milestones.append(
            {
                "event_key": f"research_started:{index}",
                "event_type": "research_started",
                "context": {"research_query": block.query},
            }
        )

    for index, block in enumerate(current_blocks):
        if index >= len(previous_blocks):
            if not block.open:
                milestones.append(
                    {
                        "event_key": f"research_complete:{index}",
                        "event_type": "research_complete",
                        "context": {"research_query": block.query},
                    }
                )
            continue
        previous_block = previous_blocks[index]
        if previous_block.open and not block.open:
            milestones.append(
                {
                    "event_key": f"research_complete:{index}",
                    "event_type": "research_complete",
                    "context": {"research_query": block.query},
                }
            )
    return milestones


def completion_milestone(
    *,
    verification_warnings: list[str],
    run_record: dict[str, Any] | None,
) -> dict[str, Any]:
    if str((run_record or {}).get("phase") or "").strip() == "awaiting_approval":
        return {
            "event_key": "approval_required",
            "event_type": "approval_required",
            "context": {},
        }
    if verification_warnings:
        return {
            "event_key": "unverified_complete",
            "event_type": "unverified_complete",
            "context": {"warning_summary": "; ".join(verification_warnings)[:280]},
        }
    return {
        "event_key": "verified_complete",
        "event_type": "verified_complete",
        "context": {},
    }


def stream_error_milestone(error: str) -> dict[str, Any]:
    return {
        "event_key": "stream_error",
        "event_type": "stream_error",
        "context": {"failure_summary": str(error or "").strip()[:280]},
    }


def publish_research_milestones_for_delta(
    *,
    thread_id: str,
    message_id: str,
    previous_content: str,
    content: str,
) -> None:
    for milestone in research_milestones_for_delta(previous_content, content):
        publish_chat_stream_event(
            thread_id,
            {
                "type": "chat_stream_milestone",
                "thread_id": thread_id,
                "message_id": message_id,
                **milestone,
            },
        )


def publish_completion_milestone(
    *,
    thread_id: str,
    message_id: str,
    verification_warnings: list[str],
    run_record: dict[str, Any] | None,
) -> None:
    publish_chat_stream_event(
        thread_id,
        {
            "type": "chat_stream_milestone",
            "thread_id": thread_id,
            "message_id": message_id,
            **completion_milestone(
                verification_warnings=verification_warnings,
                run_record=run_record,
            ),
        },
    )


def publish_stream_error_milestone(
    *,
    thread_id: str,
    message_id: str,
    error: str,
) -> None:
    publish_chat_stream_event(
        thread_id,
        {
            "type": "chat_stream_milestone",
            "thread_id": thread_id,
            "message_id": message_id,
            **stream_error_milestone(error),
        },
    )


def persist_stream_delta(
    *,
    thread_id: str,
    message_id: str,
    previous_content: str,
    accumulated: str,
    delta: str,
    updated_at: str,
) -> str:
    from app.cli_runtime.research_stream_blocks import normalize_transcript_content
    from app.terminal.agent_job_chat import merge_active_agent_job_terminals

    normalized_accumulated = normalize_transcript_content(accumulated)
    # Preserve live Axon agent-terminal job fences when Cursor assembler overwrites.
    normalized_accumulated = merge_active_agent_job_terminals(
        message_id,
        normalized_accumulated,
    )
    chat_store.update_message_content(
        message_id=message_id,
        content=normalized_accumulated,
        updated_at=updated_at,
    )
    publish_chat_stream_event(
        thread_id,
        {
            "type": "chat_stream_delta",
            "thread_id": thread_id,
            "message_id": message_id,
            "content": normalized_accumulated,
            "delta": delta,
        },
    )
    publish_research_milestones_for_delta(
        thread_id=thread_id,
        message_id=message_id,
        previous_content=previous_content,
        content=normalized_accumulated,
    )
    return normalized_accumulated

