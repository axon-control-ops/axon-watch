"""Varied, DTO-grounded KAIRO conversation replies (OP-C polish)."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from app.kairo_smalltalk import self_intro_candidates
from app.kairo_workspace_rename_intents import is_workspace_fleet_exempt_utterance
from app.operator_briefing_signals import is_bootstrap_signal

QuestionFocus = Literal[
    "approvals",
    "attention",
    "signals",
    "runs",
    "activity",
    "fleet",
    "runtime",
    "health",
    "school_operations",
    "degraded",
    "general",
    "followup",
]
_SCHOOL_OPERATIONS_RE = re.compile(
    r"\b(?:school|homework|parent(?:s|'s)?|aftercare|child(?:ren)?|learner(?:s)?|"
    r"student(?:s)?|exam(?:s)?|assessment(?:s)?|practice test(?:s)?|grading|grade)\b",
    re.IGNORECASE,
)
_OPEN_QUESTION_RE = re.compile(
    r"\b(why|how|explain|tell me (?:more|about)|what happened|what went wrong|"
    r"walk me through|can you elaborate)\b",
    re.IGNORECASE,
)
_APPROVAL_RE = re.compile(r"\b(approval|approvals|approve|awaiting)\b", re.IGNORECASE)
_SIGNAL_RE = re.compile(r"\b(signal|signals|sentry|posthog|monitor|inbox|incident)\b", re.IGNORECASE)
_RUN_RE = re.compile(r"\b(run|runs|running|executing|review|queue)\b", re.IGNORECASE)
_FLEET_RE = re.compile(r"\b(fleet|workspace|workspaces|health|nominal)\b", re.IGNORECASE)
# Bare "runtime" = CLI readiness; exclude canary/staging/production/prod/dev runtime.
_RUNTIME_RE = re.compile(
    r"\b(cli(?:\s+runtime)?|cursor(?:\s+cli)?|codex|agent\s+dispatch|lane\s+b|"
    r"vault|auth|login|api\s+key|"
    r"(?<!canary\s)(?<!staging\s)(?<!production\s)(?<!prod\s)(?<!dev\s)runtime)\b",
    re.I,
)
_HEALTH_RE = re.compile(
    r"\b("
    r"everything normal|all good|all clear|systems normal|anything wrong|"
    r"how are things|status check|is everything|are we good|you ok|you okay"
    r")\b",
    re.IGNORECASE,
)
_ATTENTION_RE = re.compile(
    r"\b(on fire|attention|urgent|wrong|needs me|needs my|priority|priorities)\b",
    re.IGNORECASE,
)
_FOLLOWUP_RE = re.compile(
    r"\b(again|still|else|anything else|what about|and what|more detail|go on)\b",
    re.IGNORECASE,
)
_ACTIVITY_RE = re.compile(
    r"\b(just did|just do|doing|latest|recent|recently|last thing|last run|activity)\b",
    re.I,
)
def is_open_style_question(content: str) -> bool:
    return bool(_OPEN_QUESTION_RE.search(content.strip()))


def detect_question_focus(content: str, *, recent_user_turns: list[str]) -> QuestionFocus:
    trimmed = content.strip()
    lower = trimmed.lower()
    if recent_user_turns and _FOLLOWUP_RE.search(lower):
        return "followup"
    # This must precede the technical "run" focus: school leadership asks are
    # consultative, not a request for a run-queue update.
    if _SCHOOL_OPERATIONS_RE.search(trimmed):
        return "school_operations"
    if _APPROVAL_RE.search(lower):
        return "approvals"
    if _ATTENTION_RE.search(lower):
        return "attention"
    if _SIGNAL_RE.search(lower):
        return "signals"
    if _RUN_RE.search(lower):
        return "runs"
    if _ACTIVITY_RE.search(lower):
        return "activity"
    if _RUNTIME_RE.search(lower):
        return "runtime"
    if _HEALTH_RE.search(lower):
        return "health"
    if _FLEET_RE.search(lower) and not is_workspace_fleet_exempt_utterance(trimmed):
        return "fleet"
    if "degraded" in lower or "connectivity" in lower or "offline" in lower:
        return "degraded"
    return "general"

def build_conversation_facts(pack: dict[str, Any]) -> dict[str, Any]:
    briefing = pack["briefing"]
    fleet = pack.get("fleet", {})
    recent_dialogue = [
        item
        for item in pack.get("recent_dialogue", [])
        if isinstance(item, dict) and str(item.get("content") or "").strip()
    ]
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
    review_ready_count = sum(
        1 for item in active_runs if str(item.get("phase") or "") == "review_ready"
    )
    dialogue_topic = ""
    for item in reversed(recent_dialogue):
        if str(item.get("role") or "").strip() == "operator":
            dialogue_topic = str(item.get("content") or "").strip()
            break
    if not dialogue_topic and recent_dialogue:
        dialogue_topic = str(recent_dialogue[-1].get("content") or "").strip()
    dialogue_topic = " ".join(dialogue_topic.split())
    if len(dialogue_topic) > 140:
        dialogue_topic = f"{dialogue_topic[:139].rstrip()}…"
    return {
        "pending_approvals": pending,
        "top_signal_title": str(top_signal.get("title", "")).strip(),
        "top_signal_summary": str(top_signal.get("summary", "")).strip(),
        "top_signal_severity": str(top_signal.get("severity", "")).strip(),
        "signal_count": len(top_signals),
        "active_run_count": len(active_runs),
        "review_ready_count": review_ready_count,
        "primary_run_summary": str(primary_run.get("summary", "")).strip(),
        "primary_run_phase": str(primary_run.get("phase", "")).strip(),
        "workspace_label": (
            str(pack.get("workspace", {}).get("display_name") or "").strip()
            or str(pack.get("workspace", {}).get("workspace_id") or "").strip()
        ),
        "notice": str(briefing.get("notice") or "").strip(),
        "advise": str(briefing.get("advise") or "").strip(),
        "degraded": bool(briefing.get("degraded", {}).get("active")),
        "watch_connected": bool(briefing.get("connectivity", {}).get("watch_connected")),
        "workspace_count": int(fleet.get("workspace_count", 0)),
        "critical_workspaces": int(fleet.get("critical_count", 0)),
        "attention_workspaces": int(fleet.get("attention_count", 0)),
        "next_action_title": str(next_actions[0].get("title", "")).strip() if next_actions else "",
        "scope_mode": str(briefing.get("scope", {}).get("mode", "fleet")),
        "cli_dispatch_ready": bool((briefing.get("cli_runtime") or {}).get("dispatch_ready", True)),
        "cli_blockers": [
            str(item).strip()
            for item in (briefing.get("cli_runtime") or {}).get("blockers", [])
            if str(item).strip()
        ],
        "recent_dialogue": recent_dialogue[-3:],
        "recent_dialogue_topic": dialogue_topic,
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
    intro = self_intro_candidates(trimmed)
    if intro:
        return _select_line(
            intro,
            session_id=session_id,
            salt=f"self:{trimmed.lower()}",
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
    if (
        not followup
        and not recent_user
        and facts.get("recent_dialogue_topic")
        and _FOLLOWUP_RE.search(content.strip())
    ):
        focus = "followup"
        followup = True
    if followup and recent_user:
        focus = detect_question_focus(recent_user[-1], recent_user_turns=recent_user[:-1])

    from app.kairo.replies.candidates import CANDIDATE_BUILDERS

    builder = CANDIDATE_BUILDERS.get(focus, CANDIDATE_BUILDERS["general"])
    candidates = [line for line in builder(facts, followup=followup) if line]
    thread_candidates: list[str] = []
    if followup and facts.get("recent_dialogue_topic"):
        topic = str(facts["recent_dialogue_topic"]).strip()
        if topic:
            thread_candidates = [
                f"From the recent thread, we were looking at this: {topic}.",
                f"Recent thread context was: {topic}.",
            ]
    if thread_candidates:
        candidates = thread_candidates if not recent_user else [*thread_candidates, *candidates]
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
