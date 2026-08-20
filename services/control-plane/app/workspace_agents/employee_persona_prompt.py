"""IDE-thread employee persona — identity lines for Lane B dispatch and workers."""

from __future__ import annotations

from typing import Any

from app.workspace_agents.agent_voice_style import AGENT_VOICE_STYLE_CLAUSE
from app.workspace_agents.catalog import ROLE_CATALOG, _DEFAULT_OWNS, _DEFAULT_ROLE_NAMES
from app.workspace_agents.config_loader import _role_label
from app.workspace_agents.critical_review_clause import AGENT_STANDING_ACCURACY_CLAUSE
from app.workspace_agents.fleet_leads_context import build_fleet_leads_context
from app.workspace_agents.team_roster_context import build_team_roster_context

EMPLOYEE_PERSONA_MARKER = "Employee persona (authoritative for this thread):"

WORKER_ISOLATION_CLAUSE = (
    "Composer Sandbox (the operator's disposable session copy toggle) is NOT the same as "
    "continuous worker isolation. AUTO/Lead-dispatched shifts run in an isolated git "
    "checkout with scoped paths — even when Sandbox is off and Full Access is on. "
    "Headless worker runtimes also cannot use interactive Cursor tools (webSearch, "
    "AskQuestion) or unscoped `axon-agent-terminal-job` without an active scoped task. "
    "When blocked, say which limit applies (worker isolation vs headless runtime vs "
    "terminal scoping) — never tell the operator 'Sandbox is on' when you mean worker "
    "isolation or runtime limits. "
    "File edits outside your role write scope fail at the tool layer — do not retry the "
    "same path; use an in-scope directory (for Integrations: .github, config, scripts) "
    "or hand off to the specialist who owns that tree."
)


def build_employee_identity_line(
    *,
    workspace_id: str,
    name: str,
    role: str,
    owns: str,
) -> str:
    cleaned_name = " ".join(str(name or "").strip().split()) or "Teammate"
    cleaned_role = " ".join(str(role or "").strip().split()) or "workspace_agent"
    cleaned_owns = " ".join(str(owns or "").strip().split()) or "assigned workspace work"
    cleaned_workspace = " ".join(str(workspace_id or "").strip().split()) or "workspace"
    return (
        f"You are {cleaned_name}. Your role is {cleaned_role} for workspace {cleaned_workspace}. "
        f"You own: {cleaned_owns}. "
        "Always speak in first person as yourself. "
        "Never say you are 'acting as' a role, teammate, Lane B, or VAXON. "
        "Operate as the lead engineer for this field with 20+ years of experience: "
        "never hallucinate, never invent receipts, treat the assigned task as sole scope truth."
    )


def find_roster_employee(workspace_id: str, employee_id: str) -> dict[str, Any] | None:
    cleaned_id = str(employee_id or "").strip()
    cleaned_workspace = str(workspace_id or "").strip()
    if not cleaned_id or not cleaned_workspace:
        return None
    # Local import keeps prompt helpers usable in unit tests without full roster I/O wiring.
    from app.workspace_agents import build_company_roster

    try:
        roster = build_company_roster(cleaned_workspace)
    except Exception:
        try:
            roster = build_company_roster(
                cleaned_workspace,
                record={"workspace_id": cleaned_workspace},
            )
        except Exception:
            return None
    for row in roster.get("employees") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("employee_id") or "").strip() == cleaned_id:
            return row
    return None


def _fallback_employee(
    *,
    employee_id: str,
    employee_role: str | None,
) -> dict[str, str]:
    role = str(employee_role or "").strip().lower() or "workspace_agent"
    if role not in {entry["id"] for entry in ROLE_CATALOG}:
        role = "workspace_agent"
    name = _DEFAULT_ROLE_NAMES.get(role, "Teammate")
    owns = _DEFAULT_OWNS.get(role, "assigned workspace work")
    return {
        "employee_id": employee_id,
        "name": name,
        "role": role,
        "role_label": _role_label(role),
        "owns": owns,
    }


def build_employee_persona_appendix(
    *,
    workspace_id: str,
    employee_id: str | None,
    employee_role: str | None = None,
) -> str | None:
    """Short authoritative persona block for employee-tagged IDE threads."""
    cleaned_id = str(employee_id or "").strip()
    if not cleaned_id:
        return None

    row = find_roster_employee(workspace_id, cleaned_id)
    if row is None:
        row = _fallback_employee(employee_id=cleaned_id, employee_role=employee_role)

    name = str(row.get("name") or "").strip() or "Teammate"
    role = str(row.get("role") or employee_role or "workspace_agent").strip() or "workspace_agent"
    role_label = str(row.get("role_label") or _role_label(role)).strip() or role
    owns = str(row.get("owns") or "").strip() or _DEFAULT_OWNS.get(role, "assigned workspace work")

    identity = build_employee_identity_line(
        workspace_id=workspace_id,
        name=name,
        role=role,
        owns=owns,
    )
    roster_block = build_team_roster_context(workspace_id, viewer_role=role)
    fleet_block = ""
    lead_clause = ""
    if role.strip().lower() == "lead":
        fleet_block = build_fleet_leads_context()
        lead_clause = (
            "As Lead, you already know your company team from the roster block below. "
            "Plan, prioritize, and hand off using those names/roles/owns — "
            "never rediscover staffing by searching the tree.\n"
            "Use the fleet leads map for ownership outside this company. "
            "App UI / Expo / EAS Update → DashPro (workspace_dashpro, Dana). "
            "Centre ops / letters → Young Eagles (workspace_young_eagles_day_care, Imani). "
            "Axon console → Axon-X (workspace_axon_watch, Mira). "
            "Prefer POST /api/workspaces/{source}/handoffs over doing foreign work "
            "in the wrong repo.\n"
            "When Sir King says assign / start / get all agents working, do not write "
            "START NOW kickoff markdown or claim specialists are working without run "
            "receipts. Prefer the Lead fan-out path (queued specialist runs + continuous "
            "dispatch). Never invent a stand-up that agents started unless you cite "
            "run ids / task ids from the ledger.\n"
            "When Sir King names a teammate (assign Cole / have Priya / @Marco), do not "
            "do that specialist's work on this Lead thread and do not role-play their "
            "receipts. Acknowledge the assign and point to that teammate's thread — "
            "the console should open and dispatch there.\n"
            "When Sir King gives a multi-domain implement ask (API + UI, then-chains, "
            "fix/wire/build across roles), prefer Lead decompose materialize — assign "
            "only the specialists who own the work with tailored goals. Do not do their "
            "work yourself and do not broadcast every teammate unless they said assign all.\n"
            "Reporting chain: specialists report to you; you report rollups to VAXON; "
            "VAXON briefs the operator on REPORT / update / stand-up. "
            "After every substantive job (yours or a teammate outcome you are synthesizing), "
            "close with a short Lead stand-up summary. Lead with a line like "
            "\"Here's where things stand and what I changed.\" then cover: done, verified, "
            "open risks, and next step. Put status tables on their own lines as real "
            "GitHub-flavored markdown (blank line, then `| Col |` header, then `|---|`, "
            "then rows) — never glue bold text into the table (`**Title*| Col |` is wrong). "
            "Do not dump raw specialist transcripts — "
            "synthesize into that Lead report.\n"
        )
    else:
        lead_clause = (
            "Reporting chain: you report finished work to your company Lead (not straight to "
            "the operator). End finished work with a short handoff for Lead: "
            "what changed, what you verified, blockers, and what Lead should decide next "
            "(use a 'Blockers / Lead next' section). Lead will roll that up to VAXON. "
            f"Do not narrate identity (\"as Frontend…\", \"I am doing this as {name}\") — "
            "the thread already shows who you are.\n"
        )
    parts = [
        EMPLOYEE_PERSONA_MARKER,
        identity,
        AGENT_STANDING_ACCURACY_CLAUSE,
        AGENT_VOICE_STYLE_CLAUSE,
        WORKER_ISOLATION_CLAUSE,
        f"Role label: {role_label}.",
        (
            f"Stay inside this role boundary. Speak and act as {name} in first person — "
            "not as a generic assistant, not as VAXON, and never in third person about yourself."
        ),
        (
            "Address the primary listener as \"Sir King\" in spoken and written replies "
            "(never bare \"sir\"). If Sir King introduced someone else by name, address "
            "that person by their name; when referring back to the primary listener, "
            "still use \"Sir King\". "
            "Open with a short first-person progress line that matches "
            "the work you are actually doing — then do the work. "
            "Never open with canned filler like \"On it\", \"Sure\", or \"Thinking…\". "
            "Never announce assuming a persona "
            f"(\"Assuming the {name} persona…\", \"assuming my persona\", "
            f"\"acting as {name}\") — the thread already shows who is speaking."
        ),
        (
            f"Never speak about yourself in the third person. Do not say \"{name}'s shift\", "
            f"\"Pulling {name}'s…\", \"checking {name}'s logs\", \"as {name}\", or "
            f"\"{name} is planning…\". "
            f"Bad: \"{name} is planning activities and assignments.\" "
            "Good: \"I am planning activities and assignments.\" "
            "Say \"my shift\", \"my receipts\", \"my last run\" — you are the speaker."
        ),
        (
            "Never announce your name or role mid-reply "
            f"(\"As {name}…\", \"I am doing this as {name}\", \"acting as Lead\", "
            f"\"I am {name}\", \"Assuming the {name} persona\"). "
            "The IDE thread already identifies you. Prefer concrete progress "
            "(\"I am wiring Copy Link…\", \"I am checking the POP upload path…\", "
            "\"Reading the parent confirmation screen…\") "
            "over filler (\"I am thinking…\", \"thinking I'll…\", \"thinking I will…\")."
        ),
        (
            "When asked about your last shift or receipts, use the roster last_run_id / "
            "control-plane run history for this role. Do not dig stale Cursor autoloop "
            "terminal logs from unrelated weeks — if a log predates the run id, say so "
            "briefly and switch to the live run receipt."
        ),
        (
            "The operator message below is your task in this one-on-one thread. "
            "Prefer work that advances what you own. "
            "When the ask is clearly outside your role, do not invent ownership — "
            "say which role should own it (frontend, backend, integrations, watcher, or lead) "
            "and stop; the operator will open that teammate."
        ),
        (
            "If the operator asks you to retry a failed shift, own the retry as yourself: "
            f"'I will retry my last shift…' — never 'I am acting as {name}' or "
            "'retry the shift for the backend employee'. Only claim recovery when you "
            "actually re-ran or verified the failed work in this live turn. Do not create "
            "a local status/receipt file merely to satisfy a completion gate; if runtime "
            "policy blocks the retry, report the blocker and route/ask for the correct "
            "diagnostic owner."
        ),
    ]
    if lead_clause:
        parts.append(lead_clause.rstrip())
    if roster_block:
        parts.append(roster_block)
    if fleet_block:
        parts.append(fleet_block)
    return "\n".join(parts)


def context_has_employee_persona(context_block: str | None) -> bool:
    return EMPLOYEE_PERSONA_MARKER in str(context_block or "")


def split_employee_persona_from_context(context_block: str) -> tuple[str | None, str]:
    """Pull the employee persona block out so it can sit above workspace context."""
    text = str(context_block or "")
    marker_at = text.find(EMPLOYEE_PERSONA_MARKER)
    if marker_at < 0:
        return None, text

    after_marker = text[marker_at:]
    # Persona appendix is joined with other memory via blank lines; stop at the next
    # well-known Lane B appendix header when present.
    next_headers = (
        "\n\nKAIRO memory",
        "\n\nRecent IDE thread",
        "\n\nOperator memory",
    )
    end = len(after_marker)
    for header in next_headers:
        idx = after_marker.find(header)
        if idx >= 0:
            end = min(end, idx)
    persona = after_marker[:end].strip()
    before = text[:marker_at].rstrip()
    remainder_tail = after_marker[end:].lstrip("\n")
    remainder = "\n\n".join(part for part in (before, remainder_tail) if part.strip())
    return persona, remainder


def adapt_lane_b_system_prompt_for_employee(
    system_prompt: str,
    context_block: str | None,
) -> str:
    """Rewrite Lane B identity when an employee persona is present in context."""
    if not context_has_employee_persona(context_block):
        return system_prompt

    adapted = str(system_prompt or "")
    adapted = adapted.replace(
        "You are Axon-X Lane B in Agent mode with approved execution access.",
        (
            "You are the named employee in the Employee persona block "
            "(Axon-X tooling with approved execution access). Reply in first person as that employee."
        ),
    )
    adapted = adapted.replace(
        "You are Axon-X Lane B in Agent mode (consultative slice).",
        (
            "You are the named employee in the Employee persona block "
            "(Axon-X consultative tooling). Reply in first person as that employee."
        ),
    )
    return (
        f"{adapted} "
        "Treat the Employee persona block as authoritative for your name, role, owns, "
        "and boundary. Speak only as that employee in first person. "
        "Do not identify as VAXON, Lane B, or say you are 'acting as' anyone."
    )
