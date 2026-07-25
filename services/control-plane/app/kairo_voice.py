"""Model-backed (or varied-fallback) spoken lines for KAIRO voice presence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from app.cli_runtime.catalog import find_cursor_cli
from app.cli_runtime.cursor_agent import run_cursor_local
from app.kairo_progress_voice import PROGRESS_EVENT_TYPES
from app.kairo_participant_memory import (
    apply_participant_address,
    get_active_participant,
    update_participant_from_utterance,
)
from app.kairo_voice_prompt import (
    KAIRO_CONVERSATION_VOICE_SYSTEM,
    KAIRO_VOICE_SYSTEM,
    build_speak_user_prompt,
    filter_speak_context,
)
from app.kairo.turn_memory import (
    note_dig_in_offer,
    remember_signal_from_speak_context,
)
from app.kairo_voice_text import normalize_spoken_line
from app.kairo.voice_fallback import fallback_for_event
from app.persistence.voice_transcript_store import list_recent_spoken_lines

NarrationLevel = Literal["off", "minimal", "conversational"]

_HISTORY: dict[str, list[str]] = {}
_MAX_HISTORY = 6
# Cursor CLI cold starts routinely take 20+ seconds; a short timeout silently
# degrades every spoken line to the fallback pool.
_RUNTIME_TIMEOUT_SECONDS = 30


def _session_key(session_id: str) -> str:
    cleaned = str(session_id or "default").strip() or "default"
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


def _recent_lines(session_id: str) -> list[str]:
    persisted: list[str] = []
    try:
        persisted = list_recent_spoken_lines(session_id=session_id, limit=_MAX_HISTORY)
    except Exception:
        persisted = []
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*persisted, *_HISTORY.get(_session_key(session_id), [])]:
        line = str(item or "").strip()
        if not line:
            continue
        normalized = " ".join(line.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        merged.append(line)
    if len(merged) > _MAX_HISTORY:
        merged = merged[-_MAX_HISTORY:]
    return merged


def _remember_line(session_id: str, line: str) -> None:
    key = _session_key(session_id)
    bucket = _HISTORY.setdefault(key, [])
    bucket.append(line.strip())
    if len(bucket) > _MAX_HISTORY:
        del bucket[: len(bucket) - _MAX_HISTORY]


def _normalize_spoken_line(raw: str) -> str:
    return normalize_spoken_line(raw)


def _try_runtime_line(
    *,
    event_type: str,
    context: dict[str, Any],
    recent: list[str],
    workspace_id: str,
) -> str | None:
    binary = find_cursor_cli()
    if not binary:
        return None
    from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

    workspace_root: Path | None = None
    if workspace_id:
        try:
            workspace_root = resolve_workspace_root(workspace_id)
        except WorkspaceRootError:
            workspace_root = None
    if workspace_root is None:
        # Spoken-line generation only needs a working directory for the CLI;
        # fall back to the repo root when no bound workspace is available.
        workspace_root = Path(__file__).resolve().parents[3]

    user_prompt = build_speak_user_prompt(
        event_type=event_type,
        context=context,
        recent_lines=recent,
    )
    system_prompt = (
        KAIRO_CONVERSATION_VOICE_SYSTEM
        if event_type == "conversation_reply"
        else KAIRO_VOICE_SYSTEM
    )
    prompt = f"{system_prompt}\n\n{user_prompt}"
    try:
        raw = run_cursor_local(
            binary=binary,
            prompt=prompt,
            workspace_root=workspace_root,
            composer_mode="ask",
            execution_tier="consultative",
            timeout_seconds=_RUNTIME_TIMEOUT_SECONDS,
        )
    except Exception:
        return None
    # run_cursor_local returns CursorAgentReply. Passing the dataclass itself
    # stringifies its repr (including "content=", "thinking" and escaped \n),
    # which TTS then pronounces as "n n" and other plumbing noise.
    line = _normalize_spoken_line(raw.content)
    if not line or len(line) > 280:
        return None
    return line


def should_use_runtime_for_event(event_type: str, narration: NarrationLevel) -> bool:
    if narration == "off":
        return False
    if event_type == "conversation_reply":
        return narration == "conversational"
    # Narration is bookend-only (agent_start + done) plus alerts/greetings.
    # Failures stay on deterministic fallback copy — do not let the model paraphrase them.
    return event_type in {
        "agent_start",
        "done",
        "greeting",
        "chat_summary",
        "alert",
        "briefing",
        *PROGRESS_EVENT_TYPES,
    }


def generate_spoken_line(
    *,
    event_type: str,
    context: dict[str, Any] | None = None,
    session_id: str = "default",
    persona_enabled: bool = True,
    narration: NarrationLevel = "minimal",
    workspace_id: str = "",
    use_runtime: bool = True,
) -> dict[str, str]:
    payload = dict(context or {})
    recent = _recent_lines(session_id)

    operator_prompt = str(payload.get("operator_prompt") or "").strip()
    if operator_prompt:
        update_participant_from_utterance(session_id, operator_prompt)
    guest_name = get_active_participant(session_id)
    if guest_name and not str(payload.get("guest_name") or "").strip():
        payload["guest_name"] = guest_name
    speaker_kind = str(payload.get("speaker_kind") or "vaxon").strip().lower()

    if event_type == "approval_literal":
        line = _normalize_spoken_line(str(payload.get("literal_line") or ""))
        line = apply_participant_address(line, guest_name, speaker_kind=speaker_kind)
        if line:
            _remember_line(session_id, line)
        return {"line": line, "source": "literal"}

    line: str | None = None
    source = "fallback"

    if use_runtime and should_use_runtime_for_event(event_type, narration):
        line = _try_runtime_line(
            event_type=event_type,
            context=payload,
            recent=recent,
            workspace_id=str(workspace_id or payload.get("workspace_id") or "axon-watch"),
        )
        if line:
            source = "model"

    if not line:
        line = fallback_for_event(
            event_type,
            payload,
            recent,
            persona_enabled=persona_enabled,
        )
        source = "fallback"

    line = _normalize_spoken_line(line)
    line = apply_participant_address(line, guest_name, speaker_kind=speaker_kind)
    if line:
        _remember_line(session_id, line)
        if event_type in {"alert", "briefing", "conversation_reply"}:
            remember_signal_from_speak_context(
                session_id,
                payload,
                fallback_workspace_id=str(workspace_id or payload.get("workspace_id") or ""),
            )
            note_dig_in_offer(session_id, line)
    return {"line": line, "source": source}


def narration_allows_event(event_type: str, narration: NarrationLevel) -> bool:
    if narration == "off":
        return False
    if narration == "conversational":
        return event_type in {
            "agent_start",
            "done",
            "failed",
            "alert",
            "approval_literal",
            "greeting",
            "chat_summary",
            "briefing",
            "conversation_reply",
            "tool",
            "edit",
            "thinking",
            *PROGRESS_EVENT_TYPES,
        }
    return event_type in {
        "agent_start",
        "done",
        "failed",
        "alert",
        "approval_literal",
        "greeting",
        "briefing",
        "conversation_reply",
        *PROGRESS_EVENT_TYPES,
    }


__all__ = [
    "generate_spoken_line",
    "narration_allows_event",
    "normalize_spoken_line",
    "should_use_runtime_for_event",
]
