"""Runtime context block for grounded KAIRO conversation turns."""

from __future__ import annotations

import re
from typing import Any

from app.chat.lane_b_agent import LaneBContext, build_lane_b_context_block
from app.kairo_chief_of_staff import build_chief_of_staff_context_block
from app.kairo_conversation_reply import build_conversation_facts
from app.kairo_participant_memory import get_active_participant
from app.operator_persona_name import OPERATOR_PERSONA_BACKRONYM, OPERATOR_PERSONA_NAME

OPEN_DETAIL_RE = re.compile(
    r"\b(walk me through|explain|tell me about|in detail|step by step|compare|tradeoffs?|everything)\b",
    re.IGNORECASE,
)
STATUS_REPORT_RE = re.compile(
    r"\b(handoff|status report|where things stand|roll.?up|brief(?:ing)? me|"
    r"what each teammate|owns next|team status|"
    r"single best next move|jarvis-style second-brain stand-up)\b",
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
    image_paths: tuple[str, ...] = (),
) -> str:
    facts = build_conversation_facts(pack)
    base = build_lane_b_context_block(
        LaneBContext(
            workspace_id=workspace_id,
            composer_mode="ask",
            image_paths=image_paths,
        )
    )
    recent_lines = [
        f'{turn.get("role", "unknown")}: {str(turn.get("content") or "").strip()}'
        for turn in recent_turns[-6:]
        if str(turn.get("content") or "").strip()
    ]
    extras = [
        # Compact reminder only — full charter is in Ask system prompt (avoid double ~7k payload).
        build_chief_of_staff_context_block(include_full_charter=False),
        "Voice assistant contract (Chief of Staff — proactive):",
        f"- You are {OPERATOR_PERSONA_NAME} ({OPERATOR_PERSONA_BACKRONYM}) — Executive Intelligence / Chief of Staff; calm, precise, one step ahead; dry wit, never theatrical.",
        "- Obey the VAXON Chief of Staff charter (system prompt + standing block). Delegate specialist implementation; do not role-play as a coding assistant.",
        "- Be proactive: when live state shows risk, degradation, approvals, or a clear next move, lead with it — do not wait to be interrogated.",
        "- Hotword REPORT / theater stand-up is a separate deterministic lane (Attention, Work in flight, Lead rollups, Fleet, Next move) — it does not use this Ask runtime. For freeform brief/status questions that reach this lane, brief only from live facts below; omit unknown charter fields rather than inventing them.",
        "- Never put a count beside Lead (say 'Lead-team plans — four of them', never 'four Lead' / '4 Lead') so speech engines do not glue 'forlead'.",
        "- Speak like a trusted mission partner: acknowledge intent, report live state, recommend the single best next move when facts support it.",
        "- If nothing urgent is true, say so briefly and offer one useful optional check — never invent work.",
        "- Razor wit when it fits; never sycophantic, never chatbot-cheerful, never invent status or capabilities.",
        '- Address the primary listener as "Sir King" — weave it naturally into the first short beat, never as a stamped header, never bare "sir".',
        '- Never open with canned filler ("On it", "Sure", "Thinking…"); lead with concrete progress or the live-state answer.',
        "- If they introduced someone else by name, address them by that name — never user/operator/human.",
        '- When a guest is active and you refer to the primary listener, use "Sir King".',
        "- Never speak punctuation or symbol names aloud (colon, slash, backslash, smiley face, emoji names, etc.).",
        "- First person, natural spoken language; ground every claim in live system state and workspace context below.",
        "- Prefer: short status → what it means → optional next step. Do not dump menus, IDs, or path chrome unless asked.",
        "- No markdown, bullets, code fences, or raw path dumps unless they asked for implementation detail.",
        (
            "- For REPORT / walkthrough / handoff: speak 4 short beats — Attention, Work in flight, "
            "Fleet, Next move — up to about 8 sentences total. Name busy teammates when roster facts "
            "are present. Do not defer with 'I'll wait then finalize' when current state is known."
            if OPEN_DETAIL_RE.search(content) or STATUS_REPORT_RE.search(content)
            else "- For quick questions: 1-3 short sentences, still include the best next move when advise/notice is present."
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
        (
            "Hierarchy: specialists report to their company Lead; Leads roll up to VAXON; "
            "VAXON briefs the operator on REPORT / update / stand-up. Prefer Lead handoff "
            "notes and live roster facts below over guessing."
        ),
    ]
    try:
        from app.workspace_agents.team_roster_context import build_team_roster_context

        roster = build_team_roster_context(workspace_id, viewer_role="lead")
        if roster:
            extras.append(roster)
    except Exception:
        pass
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
