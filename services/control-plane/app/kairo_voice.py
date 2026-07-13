"""Model-backed (or varied-fallback) spoken lines for KAIRO voice presence."""

from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path
from typing import Any, Literal

from app.cli_runtime.catalog import find_cursor_cli
from app.cli_runtime.cursor_agent import run_cursor_local
from app.kairo_persona import build_persona_voice_line
from app.kairo_progress_voice import (
    PROGRESS_EVENT_TYPES,
    PROGRESS_FALLBACK_POOLS,
    contextual_progress_fallback,
)
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
from app.kairo_voice_text import normalize_spoken_line
from app.persistence.voice_transcript_store import list_recent_spoken_lines

NarrationLevel = Literal["off", "minimal", "conversational"]

_HISTORY: dict[str, list[str]] = {}
_MAX_HISTORY = 6
# Cursor CLI cold starts routinely take 20+ seconds; a short timeout silently
# degrades every spoken line to the fallback pool.
_RUNTIME_TIMEOUT_SECONDS = 30

_FALLBACK_POOLS: dict[str, list[str]] = {
    "agent_start": [
        "Understood, sir — I'll take care of that.",
        "Right, sir — leave it with me.",
        "Very good, sir — I'll see to it now.",
        "At once, sir — I'll handle that.",
        "Consider it in hand, sir.",
    ],
    "thinking": [
        "One moment, sir — I'm working out the best approach.",
        "Give me a second, sir, to think this through.",
        "Bear with me, sir — lining up the next move.",
    ],
    "tool_read": [
        "I'm pulling up that file for you, sir.",
        "Let me fetch that from the workspace, sir.",
        "One moment, sir — reading the relevant file.",
    ],
    "tool_edit": [
        "I'm editing that file now, sir.",
        "Making the change in the workspace, sir.",
        "Updating the file as requested, sir.",
    ],
    "tool_shell": [
        "Running that command for you now, sir.",
        "Executing that in the terminal, sir.",
        "On it, sir — running the command.",
    ],
    "done": [
        "All set, sir — take a look when you're ready.",
        "Finished, sir — ready for your review.",
        "That's done on my side, sir.",
        "Complete, sir — I'll stand by for the next item.",
    ],
    "greeting": [
        "Good evening, sir — I'm here whenever you're ready.",
        "Systems are up, sir — what shall we focus on?",
        "At your service, sir — the workspace is ready.",
    ],
    **PROGRESS_FALLBACK_POOLS,
}


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


def _operator_prompt(context: dict[str, Any]) -> str:
    return str(context.get("operator_prompt") or "").strip()


def _contextual_agent_start_fallback(context: dict[str, Any]) -> str | None:
    task_summary = str(context.get("task_summary") or "").strip()
    if task_summary and task_summary.lower() not in {"done", "thinking…", "thinking...", "failed"}:
        normalized = normalize_spoken_line(task_summary, max_chars=280)
        if normalized:
            return normalized

    prompt = _operator_prompt(context)
    if not prompt:
        return None
    lower = prompt.lower()
    if "continue" in lower or "cut short" in lower:
        return "Picking up the report from where it stopped."
    if re.search(r"\bcommit\b", lower):
        return "I'll commit those changes now."
    if prompt.endswith("?") or _QUESTION_START_RE.match(lower):
        return "Good question — I'll work through that now."
    return None


def _is_failed_outcome(context: dict[str, Any]) -> bool:
    outcome = str(context.get("outcome") or "").strip().lower()
    if outcome in {"failed", "error", "failure"}:
        return True
    summary = str(context.get("failure_summary") or "").strip()
    if not summary:
        return False
    lowered = summary.lower()
    return (
        "cannot start because no cli runtime is ready" in lowered
        or "actionrequirederror" in lowered
        or "you're out of usage" in lowered
        or "api key was rejected" in lowered
    )


def _contextual_failed_fallback(context: dict[str, Any]) -> str:
    summary = str(context.get("failure_summary") or "").lower()
    if "out of usage" in summary or "actionrequirederror" in summary:
        return "That run couldn't start — Cursor usage is exhausted. Switch model or raise the limit."
    if "api key was rejected" in summary or "vault" in summary:
        return "That run couldn't start — fix the runtime keys in vault, then retry."
    return "That run couldn't start — open Runtime or vault, then retry."


def _contextual_done_fallback(context: dict[str, Any]) -> str | None:
    if _is_failed_outcome(context):
        return _contextual_failed_fallback(context)

    task_summary = str(context.get("task_summary") or "").strip()
    if task_summary and task_summary.lower() not in {"done", "failed"}:
        normalized = normalize_spoken_line(task_summary, max_chars=280)
        if normalized:
            return normalized

    prompt = _operator_prompt(context)
    lower = prompt.lower()
    edit_count = int(context.get("edit_count") or 0)

    if "continue" in lower or "cut short" in lower:
        return "That should complete the report — review when you're ready."
    if prompt.endswith("?"):
        return "There's my answer — say if you want to go deeper."
    if re.search(r"\bcommit\b", lower):
        return "Changes are committed — check the summary in the thread."
    if edit_count == 1:
        file_name = str(context.get("file_name") or "").strip()
        short = file_name.split("/")[-1] if file_name else "the file"
        return f"Done — {short} is updated."
    if edit_count > 1:
        return f"Done — {edit_count} files updated."
    if prompt:
        return "All set on my side — review when you're ready."
    return None


_QUESTION_START_RE = re.compile(
    r"^(?:what|how|why|did|do|does|can|should|were|was|is|are)\b",
    re.IGNORECASE,
)


def _strip_sir_address(line: str) -> str:
    """Neutral persona: drop JARVIS address forms — never substitute \"operator\"."""
    text = str(line or "")
    text = re.sub(r",\s*sir\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsir\s*[—-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsir,\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsir\b", "", text, flags=re.IGNORECASE)
    text = text.replace("—", "-")
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    return text.strip()


def _pick_pool_line(
    pool_key: str,
    recent: list[str],
    *,
    persona_enabled: bool,
    guest_name: str | None = None,
) -> str:
    pool = list(_FALLBACK_POOLS.get(pool_key, _FALLBACK_POOLS["done"]))
    if not persona_enabled:
        pool = [_strip_sir_address(line) for line in pool]
    elif guest_name:
        pool = [apply_participant_address(line, guest_name) for line in pool]
    recent_lower = {item.lower() for item in recent}
    for candidate in pool:
        if candidate.lower() not in recent_lower:
            return candidate
    return random.choice(pool)


def _fallback_for_event(
    event_type: str,
    context: dict[str, Any],
    recent: list[str],
    *,
    persona_enabled: bool,
) -> str:
    guest_name = str(context.get("guest_name") or "").strip() or None
    if event_type == "approval_literal":
        return str(context.get("literal_line") or "Approval required before I can continue.")

    if event_type == "alert":
        line = build_persona_voice_line(
            pending_approvals=int(context.get("pending_approvals") or 0),
            top_signal_title=str(context.get("top_signal_title") or ""),
            top_signal_workspace_id=str(context.get("top_signal_workspace_id") or ""),
            top_signal_summary=str(context.get("top_signal_summary") or ""),
            degraded_active=bool(context.get("degraded_active")),
            load_state=str(context.get("load_state") or "loaded"),
            persona_enabled=persona_enabled,
        )
        return apply_participant_address(line, guest_name)

    if event_type == "greeting":
        workspace_count = int(context.get("workspace_count") or 0)
        pending = int(context.get("pending_approvals") or 0)
        if pending > 0:
            suffix = "" if pending == 1 else "s"
            tail = f"{pending} approval{suffix} waiting for you"
        elif workspace_count > 0:
            suffix = "" if workspace_count == 1 else "s"
            tail = f"{workspace_count} workspace{suffix} bound and ready"
        else:
            tail = "workspace ready"
        line = _pick_pool_line(
            "greeting",
            recent,
            persona_enabled=persona_enabled,
            guest_name=guest_name,
        )
        return f"{line} {tail.capitalize()}."

    if event_type == "briefing":
        notice = str(context.get("notice") or "").strip()
        advise = str(context.get("advise") or "").strip()
        if notice and advise:
            return f"{notice} {advise}"
        if notice:
            return notice
        if advise:
            return advise
        return "Systems nominal — standing by for your next command."

    if event_type == "conversation_reply":
        literal = str(context.get("fallback") or context.get("reply") or "").strip()
        if literal:
            return apply_participant_address(literal, guest_name)
        return apply_participant_address(
            "Standing by for your next command.",
            guest_name,
        )

    # Tool/edit pools stay available for opt-in tool narration; the shell
    # currently filters those milestones client-side before calling speak.
    if event_type == "tool":
        tool_label = str(context.get("tool_label") or "").strip().lower()
        if tool_label.startswith("read"):
            pool_key = "tool_read"
        elif tool_label.startswith("edit"):
            pool_key = "tool_edit"
        elif tool_label.startswith("shell") or tool_label.startswith("run"):
            pool_key = "tool_shell"
        else:
            pool_key = "thinking"
        return _pick_pool_line(
            pool_key,
            recent,
            persona_enabled=persona_enabled,
            guest_name=guest_name,
        )

    if event_type == "edit":
        file_name = str(context.get("file_name") or "the file").strip() or "the file"
        line = _pick_pool_line(
            "tool_edit",
            recent,
            persona_enabled=persona_enabled,
            guest_name=guest_name,
        )
        return line.replace("that file", file_name).replace("the file", file_name)

    if event_type in {"agent_start", "run_started"}:
        contextual = _contextual_agent_start_fallback(context)
        if contextual:
            return apply_participant_address(contextual, guest_name)
        return _pick_pool_line(
            "run_started",
            recent,
            persona_enabled=persona_enabled,
            guest_name=guest_name,
        )

    if event_type == "failed":
        return apply_participant_address(_contextual_failed_fallback(context), guest_name)

    if event_type == "done":
        contextual = _contextual_done_fallback(context)
        if contextual:
            return apply_participant_address(contextual, guest_name)
        return _pick_pool_line(
            "done",
            recent,
            persona_enabled=persona_enabled,
            guest_name=guest_name,
        )

    progress = contextual_progress_fallback(event_type, context)
    if progress:
        return apply_participant_address(progress, guest_name)

    pool_key = event_type if event_type in _FALLBACK_POOLS else "done"
    return _pick_pool_line(
        pool_key,
        recent,
        persona_enabled=persona_enabled,
        guest_name=guest_name,
    )


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

    if event_type == "approval_literal":
        line = _normalize_spoken_line(str(payload.get("literal_line") or ""))
        line = apply_participant_address(line, guest_name)
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
        line = _fallback_for_event(event_type, payload, recent, persona_enabled=persona_enabled)
        source = "fallback"

    line = _normalize_spoken_line(line)
    line = apply_participant_address(line, guest_name)
    if line:
        _remember_line(session_id, line)
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
