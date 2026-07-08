"""Varied, DTO-grounded KAIRO conversation replies (OP-C polish)."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from app.operator_briefing_signals import is_bootstrap_signal

QuestionFocus = Literal[
    "approvals",
    "attention",
    "signals",
    "runs",
    "fleet",
    "degraded",
    "general",
    "followup",
]

_OPEN_QUESTION_RE = re.compile(
    r"\b(why|how|explain|tell me (?:more|about)|what happened|what went wrong|"
    r"walk me through|can you elaborate)\b",
    re.IGNORECASE,
)

_APPROVAL_RE = re.compile(r"\b(approval|approvals|approve|awaiting)\b", re.IGNORECASE)
_SIGNAL_RE = re.compile(r"\b(signal|signals|sentry|posthog|monitor|inbox|incident)\b", re.IGNORECASE)
_RUN_RE = re.compile(r"\b(run|runs|running|executing|review|queue)\b", re.IGNORECASE)
_FLEET_RE = re.compile(r"\b(fleet|workspace|workspaces|health|nominal)\b", re.IGNORECASE)
_ATTENTION_RE = re.compile(
    r"\b(on fire|attention|urgent|wrong|needs me|needs my|priority|priorities)\b",
    re.IGNORECASE,
)
_FOLLOWUP_RE = re.compile(
    r"\b(again|still|else|anything else|what about|and what|more detail|go on)\b",
    re.IGNORECASE,
)


def is_open_style_question(content: str) -> bool:
    return bool(_OPEN_QUESTION_RE.search(content.strip()))


def detect_question_focus(content: str, *, recent_user_turns: list[str]) -> QuestionFocus:
    trimmed = content.strip()
    lower = trimmed.lower()
    if recent_user_turns and _FOLLOWUP_RE.search(lower):
        return "followup"
    if _APPROVAL_RE.search(lower):
        return "approvals"
    if _ATTENTION_RE.search(lower):
        return "attention"
    if _SIGNAL_RE.search(lower):
        return "signals"
    if _RUN_RE.search(lower):
        return "runs"
    if _FLEET_RE.search(lower):
        return "fleet"
    if "degraded" in lower or "connectivity" in lower or "offline" in lower:
        return "degraded"
    return "general"


def build_conversation_facts(pack: dict[str, Any]) -> dict[str, Any]:
    briefing = pack["briefing"]
    fleet = pack.get("fleet", {})
    top_signals = [
        item
        for item in briefing.get("top_signals", [])
        if isinstance(item, dict) and not is_bootstrap_signal(item)
    ]
    active_runs = [
        item for item in briefing.get("active_runs", []) if isinstance(item, dict)
    ]
    pending = int(briefing.get("pending_approvals", {}).get("count", 0))
    next_actions = [
        item for item in briefing.get("next_safe_actions", []) if isinstance(item, dict)
    ]
    top_signal = top_signals[0] if top_signals else {}
    primary_run = active_runs[0] if active_runs else {}
    return {
        "pending_approvals": pending,
        "top_signal_title": str(top_signal.get("title", "")).strip(),
        "top_signal_summary": str(top_signal.get("summary", "")).strip(),
        "top_signal_severity": str(top_signal.get("severity", "")).strip(),
        "signal_count": len(top_signals),
        "active_run_count": len(active_runs),
        "primary_run_summary": str(primary_run.get("summary", "")).strip(),
        "primary_run_phase": str(primary_run.get("phase", "")).strip(),
        "notice": str(briefing.get("notice") or "").strip(),
        "advise": str(briefing.get("advise") or "").strip(),
        "degraded": bool(briefing.get("degraded", {}).get("active")),
        "watch_connected": bool(briefing.get("connectivity", {}).get("watch_connected")),
        "workspace_count": int(fleet.get("workspace_count", 0)),
        "critical_workspaces": int(fleet.get("critical_count", 0)),
        "attention_workspaces": int(fleet.get("attention_count", 0)),
        "next_action_title": str(next_actions[0].get("title", "")).strip() if next_actions else "",
        "scope_mode": str(briefing.get("scope", {}).get("mode", "fleet")),
    }


def _recent_assistant_lines(recent_turns: list[dict[str, str]]) -> list[str]:
    return [
        turn["content"].strip().lower()
        for turn in recent_turns
        if turn.get("role") == "assistant" and turn.get("content")
    ]


def _pick_variant(candidates: list[str], *, session_id: str, salt: str) -> str:
    cleaned = [item.strip() for item in candidates if item and item.strip()]
    if not cleaned:
        return "Systems nominal — standing by for your next command."
    digest = hashlib.sha256(f"{session_id}:{salt}".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(cleaned)
    return cleaned[index]


def _avoid_repeat(line: str, recent_assistant: list[str]) -> bool:
    normalized = line.strip().lower()
    if not normalized:
        return False
    for prior in recent_assistant[-4:]:
        if prior == normalized:
            return False
        if len(normalized) > 24 and normalized in prior:
            return False
        if len(prior) > 24 and prior in normalized:
            return False
    return True


def _select_line(
    candidates: list[str],
    *,
    session_id: str,
    salt: str,
    recent_assistant: list[str],
) -> str:
    rotated = list(candidates)
    digest = hashlib.sha256(f"{session_id}:{salt}:rotate".encode("utf-8")).hexdigest()
    offset = int(digest[:8], 16) % max(len(rotated), 1)
    rotated = rotated[offset:] + rotated[:offset]
    for candidate in rotated:
        if _avoid_repeat(candidate, recent_assistant):
            return candidate
    return _pick_variant(candidates, session_id=session_id, salt=salt)


def _approval_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    pending = int(facts["pending_approvals"])
    prefix = "Still " if followup else ""
    if pending <= 0:
        return [
            f"{prefix}No approvals are waiting — you're clear to proceed.".strip(),
            f"{prefix}Nothing needs a sign-off right now.".strip(),
            f"{prefix}Approval queue is empty on my side.".strip(),
        ]
    suffix = "" if pending == 1 else "s"
    return [
        f"{prefix}{pending} approval{suffix} waiting — I'd open Attention first.".strip(),
        f"{prefix}You have {pending} guarded run{suffix} waiting for sign-off.".strip(),
        f"{prefix}{pending} approval{suffix} on the board — Attention has the detail.".strip(),
    ]


def _attention_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    parts: list[str] = []
    pending = int(facts["pending_approvals"])
    if pending > 0:
        suffix = "" if pending == 1 else "s"
        parts.append(f"{pending} approval{suffix}")
    if facts["top_signal_title"]:
        detail = facts["top_signal_title"]
        if facts["top_signal_summary"]:
            detail = f"{detail} — {facts['top_signal_summary']}"
        parts.append(f"top signal is {detail}")
    elif int(facts["active_run_count"]) > 0:
        run_label = facts["primary_run_summary"] or "an active run"
        phase = facts["primary_run_phase"]
        if phase:
            parts.append(f"{run_label} is {phase.replace('_', ' ')}")
        else:
            parts.append(run_label)
    if not parts:
        return [
            f"{prefix}Nothing urgent — fleet looks nominal from here.".strip(),
            f"{prefix}All quiet — no fires I would interrupt you for.".strip(),
        ]
    joined = "; ".join(parts)
    return [
        f"{prefix}Here's what needs you: {joined}.".strip(),
        f"{prefix}Priority stack: {joined}.".strip(),
        f"{prefix}I'd start with {parts[0]}.".strip(),
    ]


def _signal_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if not facts["top_signal_title"]:
        return [
            f"{prefix}Inbox is quiet — no open signals worth interrupting you for.".strip(),
            f"{prefix}No monitor or inbox fires right now.".strip(),
        ]
    title = facts["top_signal_title"]
    summary = facts["top_signal_summary"]
    severity = facts["top_signal_severity"]
    if summary:
        lines = [
            f"{prefix}Top signal: {title} — {summary}".strip(),
            f"{prefix}Lead signal is {title}: {summary}".strip(),
        ]
        if severity:
            lines.append(f"{prefix}{severity.title()} signal {title} — {summary}".strip())
        return lines
    return [
        f"{prefix}Top signal is {title}.".strip(),
        f"{prefix}I'd review {title} first.".strip(),
    ]


def _run_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    count = int(facts["active_run_count"])
    if count <= 0:
        return [
            f"{prefix}No active runs in flight right now.".strip(),
            f"{prefix}Run queue is idle on my side.".strip(),
        ]
    summary = facts["primary_run_summary"] or "an operator task"
    phase = facts["primary_run_phase"].replace("_", " ")
    suffix = "" if count == 1 else "s"
    if phase:
        lines = [
            f"{prefix}{count} active run{suffix} — lead item is {summary} ({phase}).".strip(),
        ]
        if count > 1:
            lines.append(f"{prefix}{summary} is {phase}; {count - 1} other run(s) behind it.".strip())
        else:
            lines.append(f"{prefix}{summary} is {phase}.".strip())
        return lines
    return [f"{prefix}{count} active run{suffix}; lead item is {summary}.".strip()]


def _fleet_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    critical = int(facts["critical_workspaces"])
    attention = int(facts["attention_workspaces"])
    total = int(facts["workspace_count"])
    if critical > 0:
        suffix = "" if critical == 1 else "s"
        return [
            f"{prefix}{critical} workspace{suffix} in critical state across {total} bound.".strip(),
            f"{prefix}Fleet scan: {critical} critical workspace{suffix} need you.".strip(),
        ]
    if attention > 0:
        suffix = "" if attention == 1 else "s"
        return [
            f"{prefix}{attention} workspace{suffix} need attention; nothing critical.".strip(),
            f"{prefix}Fleet is stable-ish — {attention} workspace{suffix} flagged.".strip(),
        ]
    suffix = "" if total == 1 else "s"
    return [
        f"{prefix}Fleet nominal — {total} workspace{suffix} look healthy.".strip(),
        f"{prefix}All bound workspaces look green from here.".strip(),
    ]


def _general_candidates(facts: dict[str, Any], *, followup: bool) -> list[str]:
    prefix = "Still " if followup else ""
    if facts["degraded"]:
        return [
            f"{prefix}Runtime is degraded — I'd fix connectivity before dispatching more.".strip(),
            f"{prefix}We're in degraded mode — check watch/runtime health first.".strip(),
        ]
    chunks: list[str] = []
    if facts["notice"]:
        chunks.append(facts["notice"])
    if int(facts["pending_approvals"]) > 0:
        chunks.append(f"{facts['pending_approvals']} approval(s) waiting")
    if facts["top_signal_title"]:
        chunks.append(f"top signal {facts['top_signal_title']}")
    elif int(facts["active_run_count"]) > 0:
        chunks.append(f"{facts['active_run_count']} active run(s)")
    if facts["advise"] and facts["advise"] not in " ".join(chunks):
        chunks.append(facts["advise"])
    if not chunks:
        return [
            f"{prefix}All quiet on the board — standing by for your next move.".strip(),
            f"{prefix}Nothing urgent from my scan — what shall we tackle?".strip(),
            f"{prefix}Systems look nominal — I'm here when you need me.".strip(),
        ]
    body = "; ".join(chunks[:3])
    return [
        f"{prefix}{body}.".strip(),
        f"{prefix}Quick read: {body}.".strip(),
        f"{prefix}From the briefing — {body}.".strip(),
    ]


_GREETING_RE = re.compile(r"^(hi|hello|hey|good morning|good evening|good afternoon)\b", re.IGNORECASE)
_THANKS_RE = re.compile(r"^(thanks|thank you|cheers|much appreciated)\b", re.IGNORECASE)


def compose_smalltalk_reply(
    *,
    content: str,
    session_id: str,
    recent_turns: list[dict[str, str]],
) -> str | None:
    trimmed = content.strip()
    if not trimmed:
        return None
    recent_assistant = _recent_assistant_lines(recent_turns)
    if _GREETING_RE.match(trimmed):
        return _select_line(
            [
                "Good to have you — what shall we focus on?",
                "Right here when you need me — what's on your mind?",
                "Systems are live — where shall we start?",
                "At your service — what would you like to tackle first?",
            ],
            session_id=session_id,
            salt=f"greeting:{trimmed.lower()}",
            recent_assistant=recent_assistant,
        )
    if _THANKS_RE.match(trimmed):
        return _select_line(
            [
                "Any time.",
                "Happy to help.",
                "Of course — standing by if you need more.",
            ],
            session_id=session_id,
            salt=f"thanks:{trimmed.lower()}",
            recent_assistant=recent_assistant,
        )
    return None


def compose_conversation_reply(
    *,
    content: str,
    pack: dict[str, Any],
    session_id: str,
    recent_turns: list[dict[str, str]],
) -> str:
    facts = build_conversation_facts(pack)
    recent_user = [
        turn["content"]
        for turn in recent_turns
        if turn.get("role") == "user" and turn.get("content")
    ]
    recent_assistant = _recent_assistant_lines(recent_turns)
    focus = detect_question_focus(content, recent_user_turns=recent_user)
    followup = focus == "followup"
    if followup and recent_user:
        focus = detect_question_focus(recent_user[-1], recent_user_turns=recent_user[:-1])

    builders = {
        "approvals": _approval_candidates,
        "attention": _attention_candidates,
        "signals": _signal_candidates,
        "runs": _run_candidates,
        "fleet": _fleet_candidates,
        "degraded": lambda f, *, followup: _general_candidates(f, followup=followup),
        "general": _general_candidates,
        "followup": _general_candidates,
    }
    builder = builders.get(focus, _general_candidates)
    candidates = [line for line in builder(facts, followup=followup) if line]
    return _select_line(
        candidates,
        session_id=session_id,
        salt=f"{focus}:{content.strip().lower()}",
        recent_assistant=recent_assistant,
    )


def build_converse_speak_context(
    *,
    operator_prompt: str,
    pack: dict[str, Any],
    reply: str,
    recent_turns: list[dict[str, str]],
) -> dict[str, Any]:
    facts = build_conversation_facts(pack)
    return {
        "operator_prompt": operator_prompt,
        "reply": reply,
        "fallback": reply,
        "pending_approvals": facts["pending_approvals"],
        "top_signal_title": facts["top_signal_title"],
        "active_run_count": facts["active_run_count"],
        "degraded_active": facts["degraded"],
        "recent_turns": recent_turns[-4:],
    }


__all__ = [
    "build_conversation_facts",
    "build_converse_speak_context",
    "compose_conversation_reply",
    "compose_smalltalk_reply",
    "detect_question_focus",
    "is_open_style_question",
]
