"""Deterministic fallback builder for specialist-aware Instructions markdown."""

from __future__ import annotations

import re

from app.specialist_roles import (
    GENERAL_ROLE_ID,
    SPECIALIST_ROLE_IDS,
    SpecialistContext,
    role_profile,
)


def _summarize_goal(source: str) -> str:
    cleaned = re.sub(r"\s+", " ", source.strip())
    if not cleaned:
        return "Complete the operator request."
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0].strip()
    if len(first_sentence) >= 24:
        return first_sentence
    return cleaned[:220].rstrip(" ,.;") + ("..." if len(cleaned) > 220 else "")


def _infer_scope_bullets(source: str, context: SpecialistContext) -> list[str]:
    lowered = source.lower()
    candidates: list[str] = []
    mappings = [
        ("workspace", "Configure and validate the requested workspace integration"),
        ("teacher", "Model Teacher-X behaviour as a real in-app teacher user"),
        ("layout", "Review app layout, navigation, and screen discoverability"),
        ("feature", "Exercise and validate the relevant product features end-to-end"),
        ("screen", "Verify the named screens and user flows in the live app"),
        ("homework", "Cover homework creation, assignment, and parent/teacher visibility"),
        ("assignment", "Cover assignment workflows, submission, and grading paths"),
        ("grading", "Validate grading flows and reporting outputs"),
        ("report", "Validate report generation and export/share behaviour"),
        ("language", "Verify multilingual support across official South African languages"),
        ("parent", "Validate parent-facing journeys and notifications"),
        ("principal", "Validate principal/admin operational workflows"),
        ("axon-x", "Use Axon-X fleet workflows to drive discovery, fixes, and upgrades"),
        ("bug", "Log, reproduce, and fix defects encountered during holistic testing"),
    ]
    for needle, bullet in mappings:
        if needle in lowered and bullet not in candidates:
            candidates.append(bullet)
    if not candidates:
        for sentence in re.split(r"(?<=[.!?])\s+", source.strip()):
            trimmed = sentence.strip(" \"'")
            if len(trimmed) >= 24:
                candidates.append(trimmed[:160])
            if len(candidates) >= 6:
                break
    if not candidates:
        candidates.append("Execute only what the source request describes")
    if context.role in SPECIALIST_ROLE_IDS:
        profile = context.profile
        role_items = [
            f"{profile.display_name} owned work: {item}"
            for item in profile.primary_responsibilities[:2]
        ]
        candidates = role_items + candidates
    return candidates[:8]


def _infer_steps(source: str, context: SpecialistContext) -> list[str]:
    role = context.role
    steps = [
        "Read the source request and restate the Goal, acceptance checks, and anything explicitly out of scope.",
        "Confirm role ownership and workspace scope before changing anything.",
    ]
    role_steps = {
        "lead": "Decompose implementation work into owned specialist tasks with sequence, dependencies, and evidence requirements.",
        "watcher": "Reproduce or inspect the reported behaviour read-only and capture expected-versus-actual evidence.",
        "frontend": "Inspect the relevant client routes, components, state, responsive layout, and visible error/loading states.",
        "backend": "Inspect the relevant server routes, persistence, authorization, schemas, jobs, and failure paths.",
        "integrations": "Inspect the relevant external API, auth, webhook, callback, mapping, retry, and secret-boundary contracts.",
    }
    steps.append(
        role_steps.get(
            role,
            "Map the requested product areas to concrete screens, roles, and workflows before changing anything.",
        )
    )
    for bullet in _infer_scope_bullets(source, context)[:4]:
        steps.append(f"Exercise and document: {bullet}. Capture screenshots, broken flows, and missing capabilities.")
    steps.extend(
        [
            "When Axon-X or the product fleet is part of the request, run the work through that workflow and record fixes or upgrades discovered.",
            "Verify the requested outcomes on web and mobile where applicable; note any feature that requires a native rebuild instead of OTA.",
            "Create handoffs for any work outside the selected specialist's authority.",
            "Summarize implemented changes, validation evidence, handoffs, remaining gaps, and the next operator action without claiming git/release work that was not requested.",
        ]
    )
    return steps[:9]


def _infer_context(source: str, context: SpecialistContext) -> str:
    lowered = source.lower()
    if context.role == GENERAL_ROLE_ID:
        return (
            "Convert the operator's plain-language request into a delivery-ready task brief. "
            "No specialist role was supplied. Confirm ownership before implementation."
        )
    if any(token in lowered for token in ("lila", "cole", "imani", "agent", "workspace-delivery", "direct chat")):
        return (
            "Convert the operator's plain-language request into a delivery-ready task brief. "
            "Avoid the prior failure mode where an agent produced a useful answer or diff but "
            "the run did not land a file change because it was not executed as a properly scoped "
            "workspace-delivery task."
        )
    return (
        "Convert the operator's plain-language request into a delivery-ready task brief. "
        "Preserve the requested outcome, make implicit work explicit, and keep execution scope "
        "narrow enough that the assignee can verify the result with receipts."
    )


def _infer_delivery_mode_bullets(source: str, context: SpecialistContext) -> list[str]:
    lowered = source.lower()
    if context.role in SPECIALIST_ROLE_IDS:
        profile = context.profile
        scope = ", ".join(context.write_scope or context.allowed_paths) or "scope must be confirmed before implementation"
        bullets = [
            f"Required run type: {profile.preferred_delivery_mode}",
            f"Required workspace: {context.workspace_label or context.workspace_id or 'selected workspace'}",
            f"Required read scope: {', '.join(context.read_scope) if context.read_scope else 'workspace-readable context'}",
            f"Required write scope: {scope}",
            "Required receipts: changed-file receipt when files change, validation receipt, and final report with handoffs.",
        ]
        if context.role == "watcher":
            bullets[0] = "Required run type: read-only verification task unless explicitly reassigned"
            bullets[3] = "Required write scope: none by default; report and hand off product-file changes"
        if context.role == "lead":
            bullets[0] = "Required run type: planning or orchestration task followed by owned specialist delivery tasks"
        if context.role == "integrations":
            bullets.append("External integration changes require secret-safe integration-delivery evidence.")
        return bullets
    bullets = [
        "Run this as a scoped workspace-delivery task when code or file changes are required; do not handle implementation as a direct chat-only answer.",
        "Select the correct workspace before starting, and include the relevant app/service paths in the writable delivery scope.",
        "Require a delivery receipt that names the changed files and the validation commands that ran.",
    ]
    if any(token in lowered for token in ("frontend", "ui", "screen", "button", "command-centre", "assets/app.js", "lila")):
        bullets.append("For frontend work, ensure the frontend role can write the relevant UI path before claiming the edit landed.")
    if any(token in lowered for token in ("backend", "api", "supabase", "database", "cole")):
        bullets.append("For backend or integration work, confirm the backend role owns any API, database, or service changes before handing off.")
    return bullets[:5]


def _infer_acceptance_criteria(source: str, context: SpecialistContext) -> list[str]:
    lowered = source.lower()
    criteria = [
        "The requested behaviour is visible in the actual target workspace or app, not only described in an agent reply.",
        "Every changed file appears in the delivery receipt for the run that claims completion.",
        "The final report separates implemented changes, verified outcomes, and any remaining assumptions.",
    ]
    if any(token in lowered for token in ("button", "ui", "screen", "form", "render", "frontend")):
        criteria.append("The affected UI state can be reproduced from the relevant screen without relying on stale cached output.")
    if any(token in lowered for token in ("test", "check", "validation", "verify")):
        criteria.append("The named check or an appropriate local validation command passes after the change.")
    if context.role in SPECIALIST_ROLE_IDS:
        criteria.extend(context.profile.required_evidence[:3])
    return criteria


def _infer_validation_bullets(source: str, context: SpecialistContext) -> list[str]:
    lowered = source.lower()
    bullets = [
        "Run the narrowest local validation command that covers the changed path.",
        "If no automated test exists, perform a manual smoke check and record exactly what was checked.",
    ]
    if context.role in SPECIALIST_ROLE_IDS:
        bullets.extend(context.profile.validation_expectations[:6])
    if any(token in lowered for token in ("frontend", "ui", "screen", "button", "vite", "vue", "typescript")):
        bullets.append("Run the frontend typecheck or equivalent UI validation for the affected package.")
    if any(token in lowered for token in ("backend", "api", "python", "pytest", "supabase")):
        bullets.append("Run the relevant backend pytest or API smoke command for the affected service.")
    bullets.append("Do not mark the task complete until the validation result is attached to the handoff.")
    return bullets


def _format_assigned_specialist(context: SpecialistContext) -> list[str]:
    profile = context.profile
    return [
        f"- Role: {profile.display_name}",
        f"- Agent: {context.agent_name or 'Unspecified'}",
        f"- Workspace: {context.workspace_label or context.workspace_id or 'Unspecified'}",
        f"- Delivery mode: {context.requested_delivery_mode or profile.preferred_delivery_mode}",
    ]


def _ownership_sections(context: SpecialistContext) -> list[str]:
    profile = context.profile
    owned = [f"- {item}" for item in profile.primary_responsibilities]
    handoffs = [f"- {item}" for item in profile.handoff_rules]
    if context.role == GENERAL_ROLE_ID:
        owned = ["- No specialist role was supplied. Confirm ownership before implementation."]
    if context.mismatch_reason:
        handoffs.append(f"- Resolve context mismatch before implementation: {context.mismatch_reason}")
    return ["### Owned by this specialist", *owned, "", "### Requires handoff", *handoffs]


def _handoff_bullets(context: SpecialistContext) -> list[str]:
    if context.role == GENERAL_ROLE_ID:
        return [
            "Recipient specialist: Lead or the correct owner once ownership is confirmed",
            "Reason: No verified specialist context was supplied",
            "Evidence or inputs supplied: source request and workspace identifier",
            "Expected output: owned delivery task or verification report",
            "Blocking status: blocking for implementation",
        ]
    profile = context.profile
    return [
        f"Recipient specialist: as required by {profile.display_name} handoff rules",
        "Reason: any requested work outside this specialist's ownership boundaries",
        "Evidence or inputs supplied: source request, inspected files, run receipts, and validation results",
        "Expected output: owned implementation, verification, or decision receipt from the receiving specialist",
        "Blocking status: mark blocking when the selected specialist owns none of the requested implementation",
    ]


def build_fallback_instructions_markdown(
    source: str,
    context: SpecialistContext | None = None,
    *,
    git_actions_requested: bool = False,
) -> str:
    cleaned = source.strip()
    context = context or SpecialistContext(role=GENERAL_ROLE_ID)
    profile = role_profile(context.role)
    out_of_scope = [
        "Committing, pushing, merging, tagging, or releasing unless explicitly requested",
        "Inventing unrelated refactors, migrations, or cleanup chores",
    ]
    if git_actions_requested:
        out_of_scope = [item for item in out_of_scope if "Committing" not in item]
    constraints = [
        "Follow only the steps listed above",
        "Treat Out of scope as binding",
        "Preserve every explicit requirement from the source request",
        "Do not infer specialist authority from agent names",
        *profile.restricted_actions,
        "Call out native-build-only gaps separately from OTA-safe fixes",
        "Do not deploy, publish, or notify external parties unless explicitly requested",
        "Do not claim work was implemented, tested, or verified without evidence",
    ]

    lines = ["# Instructions", ""]
    if context.role in SPECIALIST_ROLE_IDS:
        lines += [
            "## Assigned specialist",
            *_format_assigned_specialist(context),
            "",
            "## Role mandate",
            profile.mission,
            "",
            "## Ownership boundaries",
            *_ownership_sections(context),
            "",
        ]
    lines += [
        "## Goal",
        _summarize_goal(cleaned),
        "",
        "## Context",
        _infer_context(cleaned, context),
        "",
        "## Delivery mode",
        *[f"- {item}" for item in _infer_delivery_mode_bullets(cleaned, context)],
        "",
        "## In scope",
        *[f"- {item}" for item in _infer_scope_bullets(cleaned, context)],
        "",
        "## Out of scope",
        *[f"- {item}" for item in out_of_scope],
        "",
        "## Steps",
        *[f"{index}. {step}" for index, step in enumerate(_infer_steps(cleaned, context), start=1)],
        "",
        "## Acceptance criteria",
        *[f"- {item}" for item in _infer_acceptance_criteria(cleaned, context)],
        "",
        "## Validation",
        *[f"- {item}" for item in _infer_validation_bullets(cleaned, context)],
        "",
        "## Handoff",
        *[f"- {item}" for item in _handoff_bullets(context)],
        "",
        "## Constraints",
        *[f"- {item}" for item in constraints],
        "",
        "## Source request",
        cleaned,
        "",
    ]
    return "\n".join(lines)
