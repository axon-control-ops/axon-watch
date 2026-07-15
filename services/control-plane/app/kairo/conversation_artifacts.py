"""Runtime artifact and assistant reply helpers for KAIRO conversation."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from app.cli_runtime.router import dispatch_ide_composer
from app.kairo_conversation_reply import build_conversation_facts, compose_conversation_reply
from app.kairo_conversation_runtime_context import (
    OPEN_DETAIL_RE,
    build_runtime_context_block,
    runtime_workspace_id,
)
from app.kairo_voice import normalize_spoken_line

ConversationSource = Literal["template", "model", "fallback"]
ConversationAnswerTier = Literal["fast", "deep"]
_MAX_RUNTIME_VOICE_REPLY_CHARS = 1200


def short_reply_summary(reply: str, *, max_chars: int = 280) -> str:
    trimmed = re.sub(r"\s+", " ", reply.strip())
    if not trimmed:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", trimmed)
    summary = ""
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        next_summary = f"{summary} {candidate}".strip()
        if len(next_summary) > max_chars:
            break
        summary = next_summary
        if summary.count(".") + summary.count("!") + summary.count("?") >= 2:
            break
    if summary:
        return summary
    if len(trimmed) <= max_chars:
        return trimmed
    shortened = trimmed[: max_chars - 1].rstrip(" ,;:")
    return f"{shortened}…"


def artifact_handoff_action(
    *,
    pack: dict[str, Any],
    signal_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, object] | None:
    briefing = pack.get("briefing", {})
    top_signals = [
        item for item in briefing.get("top_signals", []) if isinstance(item, dict)
    ]
    signal: dict[str, Any] | None = None
    if signal_id:
        for candidate in top_signals:
            if str(candidate.get("signal_id", "")).strip() == signal_id:
                signal = candidate
                break
    if signal is None and top_signals:
        signal = top_signals[0]
    if signal is None:
        resolved_workspace_id = str(workspace_id or "").strip()
        resolved_signal_id = str(signal_id or "").strip()
        if not resolved_workspace_id or not resolved_signal_id:
            return None
        task = f"Investigate signal {resolved_signal_id}"
        return {
            "type": "handoff_ide",
            "signal_id": resolved_signal_id,
            "target_workspace_id": resolved_workspace_id,
            "task": task,
        }
    resolved_workspace_id = (
        str(workspace_id or signal.get("workspace_id") or "").strip() or None
    )
    resolved_signal_id = str(signal.get("signal_id") or "").strip()
    title = str(signal.get("title") or "signal").strip()
    summary = str(signal.get("summary") or "").strip()
    if not resolved_workspace_id or not resolved_signal_id:
        return None
    task = f'Investigate signal "{title}"'
    if summary:
        task = f"{task}: {summary}"
    return {
        "type": "handoff_ide",
        "signal_id": resolved_signal_id,
        "target_workspace_id": resolved_workspace_id,
        "task": task,
    }


def build_runtime_artifact(
    *,
    content: str,
    reply: str,
    pack: dict[str, Any],
    signal_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, object]:
    facts = build_conversation_facts(pack)
    artifact_id = f"artifact_{hashlib.sha256((content + reply).encode('utf-8')).hexdigest()[:12]}"
    summary = short_reply_summary(reply)
    title = facts["top_signal_title"] or "VAXON analysis"
    sources: list[dict[str, str]] = []
    if facts["top_signal_title"]:
        detail = facts["top_signal_summary"] or facts["top_signal_title"]
        sources.append({"label": "Top signal", "detail": detail})
    if facts["notice"]:
        sources.append({"label": "Briefing notice", "detail": facts["notice"]})
    if facts["advise"]:
        sources.append({"label": "Briefing advise", "detail": facts["advise"]})
    if not sources:
        sources.append({"label": "Briefing", "detail": "Grounded in current fleet and run state."})
    actions: list[dict[str, object]] = []
    handoff = artifact_handoff_action(
        pack=pack,
        signal_id=signal_id,
        workspace_id=workspace_id,
    )
    if handoff:
        actions.append({"label": "Continue in IDE", "ui_action": handoff})
    return {
        "artifact_id": artifact_id,
        "title": title,
        "summary": summary or "Analysis ready.",
        "body": reply,
        "sources": sources,
        "actions": actions,
    }


def should_use_runtime_for_open_question(
    *,
    content: str,
    use_runtime: bool,
    answer_tier: ConversationAnswerTier,
) -> bool:
    if not use_runtime:
        return False
    if answer_tier == "deep":
        return True
    return bool(OPEN_DETAIL_RE.search(content))


def runtime_assistant_reply(
    *,
    content: str,
    session_id: str,
    workspace_id: str | None,
    pack: dict[str, Any],
    recent_turns: list[dict[str, str]],
    context_node_id: str | None = None,
    context_signal_id: str | None = None,
) -> tuple[str, ConversationSource]:
    resolved_workspace_id = runtime_workspace_id(workspace_id=workspace_id, pack=pack)
    context_block = build_runtime_context_block(
        content=content,
        workspace_id=resolved_workspace_id,
        pack=pack,
        session_id=session_id,
        recent_turns=recent_turns,
        context_node_id=context_node_id,
        context_signal_id=context_signal_id,
    )
    payload = dispatch_ide_composer(
        workspace_id=resolved_workspace_id,
        composer_mode="ask",
        user_prompt=content,
        context_block=context_block,
        execution_access="consultative",
    )
    reply = normalize_spoken_line(
        str(payload.get("content") or ""),
        max_chars=_MAX_RUNTIME_VOICE_REPLY_CHARS,
    )
    if not reply:
        return (
            compose_conversation_reply(
                content=content,
                pack=pack,
                session_id=session_id,
                recent_turns=recent_turns,
            ),
            "fallback",
        )
    return reply, ("model" if bool(payload.get("dispatched")) else "fallback")
