"""Deterministic spoken-line fallback pools for KAIRO voice."""

from __future__ import annotations

import random
import re
from typing import Any

from app.kairo_participant_memory import apply_participant_address
from app.kairo_persona import build_persona_voice_line
from app.kairo_progress_voice import PROGRESS_FALLBACK_POOLS, contextual_progress_fallback
from app.kairo_voice_text import normalize_spoken_line

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

_QUESTION_START_RE = re.compile(
    r"^(?:what|how|why|did|do|does|can|should|were|was|is|are)\b",
    re.IGNORECASE,
)


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


def fallback_for_event(
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


__all__ = ["fallback_for_event"]
