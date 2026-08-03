"""Pure classification of KAIRO operator conversation turns."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from app.chat.command_intent import classify_command, expand_command_shortcuts, is_question
from app.kairo.operator_input_safety import is_pasted_operational_context
from app.kairo_conversation_reply import is_open_style_question

ConversationTurnKind = Literal["status_question", "open_question", "command", "chat", "action"]

_STATUS_HINT_RE = re.compile(
    r"\b(approval|approvals|attention|on fire|status|briefing|fleet|health|"
    r"signal|signals|running|active run|what needs|what's wrong|what is wrong|"
    r"happening|nominal|degraded|waiting|clear)\b",
    re.IGNORECASE,
)
_WORKSPACE_ACTIVITY_RE = re.compile(
    r"(?:\b(check|show|tell me|what|pull up)\b[\w\s,-]*)?"
    r"\b(workspace|dashpro|axon[\s-]*watch|axon[\s-]*local)\b"
    r"[\w\s,-]*\b(check|show|what|pull up)?\b[\w\s,-]*"
    r"\b(just did|doing|latest|recent|activity)\b",
    re.IGNORECASE,
)


def classify_conversation_turn(
    content: str,
    *,
    classify_command_fn: Callable[[str], str] = classify_command,
    expand_command_shortcuts_fn: Callable[[str], str] = expand_command_shortcuts,
    is_question_fn: Callable[[str], bool] = is_question,
) -> ConversationTurnKind:
    trimmed = content.strip()
    if not trimmed:
        return "chat"
    if is_pasted_operational_context(trimmed):
        return "status_question"
    if classify_command_fn(expand_command_shortcuts_fn(trimmed)) != "unsupported":
        return "command"
    if is_open_style_question(trimmed):
        return "open_question"
    if _WORKSPACE_ACTIVITY_RE.search(trimmed):
        return "status_question"
    if _STATUS_HINT_RE.search(trimmed):
        return "status_question"
    if is_question_fn(trimmed):
        return "open_question"
    return "chat"
