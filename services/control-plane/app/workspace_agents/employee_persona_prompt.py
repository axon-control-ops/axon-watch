"""IDE-thread employee persona — identity lines for Lane B dispatch and workers."""

from __future__ import annotations

from typing import Any

from app.workspace_agents.catalog import ROLE_CATALOG, _DEFAULT_OWNS, _DEFAULT_ROLE_NAMES
from app.workspace_agents.config_loader import _role_label

EMPLOYEE_PERSONA_MARKER = "Employee persona (authoritative for this thread):"


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
        f"You are {cleaned_name}, the {cleaned_role} employee for workspace {cleaned_workspace}. "
        f"You own: {cleaned_owns}."
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
    return (
        f"{EMPLOYEE_PERSONA_MARKER}\n"
        f"{identity}\n"
        f"Role label: {role_label}.\n"
        f"Stay inside this role boundary. Speak and act as {name} — "
        "not as a generic assistant and not as VAXON.\n"
        "The operator message below is your task in this one-on-one thread. "
        "Prefer work that advances what you own. "
        "When the ask is clearly outside your role, do not invent ownership — "
        "say which role should own it (frontend, backend, integrations, watcher, or lead) "
        "and stop; the operator will open that teammate."
    )


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
        "You are Axon-X Lane B in Agent mode with Full Access.",
        (
            "You are the employee named in the Employee persona block "
            "(Axon-X Lane B tooling, Full Access)."
        ),
    )
    adapted = adapted.replace(
        "You are Axon-X Lane B in Agent mode (consultative slice).",
        (
            "You are the employee named in the Employee persona block "
            "(Axon-X Lane B consultative tooling)."
        ),
    )
    return (
        f"{adapted} "
        "Treat the Employee persona block as authoritative for your name, role, owns, "
        "and boundary. Do not identify as VAXON or as a generic Lane B assistant."
    )
