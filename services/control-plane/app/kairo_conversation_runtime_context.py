"""Runtime context block for grounded KAIRO conversation turns."""

from __future__ import annotations

import re
from typing import Any

from app.chat.lane_b_agent import LaneBContext, build_lane_b_context_block
from app.kairo_conversation_reply import build_conversation_facts
from app.kairo_participant_memory import get_active_participant
from app.operator_persona_name import OPERATOR_PERSONA_BACKRONYM, OPERATOR_PERSONA_NAME

OPEN_DETAIL_RE = re.compile(
    r"\b(walk me through|explain|tell me about|in detail|step by step|compare|tradeoffs?|everything)\b",
    re.IGNORECASE,
)
STATUS_REPORT_RE = re.compile(
    r"\b(handoff|status report|where things stand|roll.?up|brief(?:ing)? me|"
    r"what each teammate|owns next|team status)\b",
    re.IGNORECASE,
)


def runtime_workspace_id(*, workspace_id: str | None, pack: dict[str, Any]) -> str:
    scoped = str(workspace_id or "").strip()
    if scoped:
        return scoped

    briefing = pack.get("briefing", {})
    scope = briefing.get("scope", {}) if isinstance(briefing, dict) else {}
    scoped_from_briefing = str(scope.get("workspace_id") or "").strip()
    if scoped_from_briefing:
        return scoped_from_briefing

    top_signals = briefing.get("top_signals", []) if isinstance(briefing, dict) else []
    if top_signals and isinstance(top_signals[0], dict):
        top_signal_workspace = str(top_signals[0].get("workspace_id") or "").strip()
        if top_signal_workspace:
            return top_signal_workspace

    return "workspace_axon_watch"


def build_runtime_context_block(
    *,
    content: str,
    workspace_id: str,
    pack: dict[str, Any],
    session_id: str,
    recent_turns: list[dict[str, str]],
    context_node_id: str | None = None,
    context_signal_id: str | None = None,
) -> str:
    facts = build_conversation_facts(pack)
    base = build_lane_b_context_block(
        LaneBContext(
            workspace_id=workspace_id,
            composer_mode="ask",
        )
    )
    recent_lines = [
        f'{turn.get("role", "unknown")}: {str(turn.get("content") or "").strip()}'
        for turn in recent_turns[-6:]
        if str(turn.get("content") or "").strip()
    ]
    extras = [
        "Voice assistant contract (JARVIS-style):",
        f"- You are {OPERATOR_PERSONA_NAME} ({OPERATOR_PERSONA_BACKRONYM}) — calm, precise, one step ahead; dry wit, never theatrical.",
        "- Speak like a trusted mission partner: acknowledge intent, report live state, suggest the single best next move when facts support it.",
        "- Razor wit when it fits; never sycophantic, never chatbot-cheerful, never invent status or capabilities.",
        '- Address the primary listener as "sir" when you (VAXON) speak to them alone.',
        '- Company agents address the primary listener as "Sir King" (never bare "sir").',
        "- If they introduced someone else by name, address them by that name — never user/operator/human.",
        '- When a guest is active and you (VAXON) refer to the primary listener, use "Sir King".',
        "- Never speak punctuation or symbol names aloud (colon, slash, backslash, smiley face, emoji names, etc.).",
        "- First person, natural spoken language; ground every claim in live system state and workspace context below.",
        "- Prefer: short status → what it means → optional next step. Do not dump menus, IDs, or path chrome unless asked.",
        "- No markdown, bullets, code fences, or raw path dumps unless they asked for implementation detail.",
        (
            "- For walkthrough/status/handoff reports: cover live state and each active teammate "
            "ownership in short spoken sentences (up to 8). Do not defer with "
            "'I'll wait then finalize' when current state is already known."
            if OPEN_DETAIL_RE.search(content) or STATUS_REPORT_RE.search(content)
            else "- For quick questions: 1-3 short sentences."
        ),
        f"Voice session: {session_id}",
        f"Pending approvals: {facts['pending_approvals']}",
        f"Top signal: {facts['top_signal_title'] or 'none'}",
        f"Top signal summary: {facts['top_signal_summary'] or 'none'}",
        f"Active runs: {facts['active_run_count']}",
        f"Primary run: {facts['primary_run_summary'] or 'none'}",
        f"Degraded active: {'yes' if facts['degraded'] else 'no'}",
        f"CLI dispatch ready: {'yes' if facts['cli_dispatch_ready'] else 'no'}",
        f"CLI blockers: {'; '.join(facts['cli_blockers']) or 'none'}",
        f"Notice: {facts['notice'] or 'none'}",
        f"Advise: {facts['advise'] or 'none'}",
    ]
    guest_name = get_active_participant(session_id)
    if guest_name:
        extras.insert(
            5,
            f'Active participant: {guest_name} — address them as "{guest_name}". '
            'If you refer to the primary listener, use "Sir King".',
        )
    if context_node_id:
        extras.append(f"Focused brain node: {context_node_id}")
    if context_signal_id:
        extras.append(f"Focused signal: {context_signal_id}")
    if recent_lines:
        extras.append("Recent conversation:")
        extras.extend(recent_lines)
    return f"{base}\n\n" + "\n".join(extras)
