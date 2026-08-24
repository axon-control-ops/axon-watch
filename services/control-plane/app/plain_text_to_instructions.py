"""Parse Instructions markdown and detect binding out-of-scope git gates."""

from __future__ import annotations

import re

from app.specialist_roles import (
    GENERAL_ROLE_ID,
    SPECIALIST_ROLE_IDS,
    SpecialistContext,
    role_profile,
)

_INSTRUCTIONS_HEADING_RE = re.compile(r"^#\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_ALT_INSTRUCTIONS_HEADING_RE = re.compile(r"^##\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_FENCED_MARKDOWN_RE = re.compile(
    r"^```(?:markdown|md)?\s*\r?\n([\s\S]*?)\r?\n```\s*$",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(
    r"^##\s*(Assigned specialist|Role mandate|Ownership boundaries|Goal|Context|Delivery mode|In scope|Out of scope|Steps|Acceptance criteria|Validation|Handoff|Constraints|Assumptions|Source request)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_BASE_REQUIRED_SECTION_KEYS = (
    "goal",
    "context",
    "delivery_mode",
    "in_scope",
    "out_of_scope",
    "steps",
    "acceptance_criteria",
    "validation",
    "constraints",
)
_SPECIALIST_REQUIRED_SECTION_KEYS = (
    "assigned_specialist",
    "role_mandate",
    "ownership_boundaries",
    *_BASE_REQUIRED_SECTION_KEYS,
)
_REQUIRED_SECTION_KEYS = _BASE_REQUIRED_SECTION_KEYS
_OPTIONAL_SECTION_KEYS = ("handoff", "assumptions", "source_request")
_MIN_STEP_LINES = 4
_GIT_OUT_OF_SCOPE_RE = re.compile(
    r"\b(?:commit(?:ting|s)?|push(?:ing|es)?|merg(?:e|ing)|releas(?:e|ing))\b",
    re.IGNORECASE,
)
_NEGATED_COMMIT_RE = re.compile(
    r"\b(?:never|don'?t|do\s+not|did\s+not|no|not|without|wrong)\b"
    r"(?:\s+\w+){0,8}\s+(?:\w+\s+){0,4}?"
    r"(?:commit(?:ting|s)?|push(?:ing|es)?|merg(?:e|ing)|releas(?:e|ing))\b",
    re.IGNORECASE,
)
_AFFIRMATIVE_COMMIT_RE = re.compile(
    r"(?:"
    r"^\s*(?:ok(?:ay)?[,\s]+)?(?:please\s+)?commit\b"
    r"(?:\s+(?:first|these|my|the|all|current|pending|this|those))?"
    r"(?:\s+changes?)?(?:\s+and\s+push)?"
    r"|(?:^|[\s,.:;!\-—])(?:please\s+)?commit\s+"
    r"(?:first|these|my|the|all|current|pending|this|those|changes?\b)"
    r"(?:\s+changes?)?(?:\s+and\s+push)?"
    r"|(?:^|[\s,.:;!\-—])(?:please\s+)?commit\s+and\s+(?![0-9a-f]{7,40}\b)\w+\b"
    r"|(?:^|[\s,.:;!\-—])(?:create\s+(?:a\s+)?commit|git\s+commit)\b"
    r")",
    re.IGNORECASE,
)


def _parse_sections(prompt: str) -> dict[str, str]:
    hits = list(_SECTION_RE.finditer(prompt))
    sections: dict[str, str] = {}
    for index, found in enumerate(hits):
        key = found.group(1).lower().replace(" ", "_")
        body_start = found.end()
        body_end = hits[index + 1].start() if index + 1 < len(hits) else len(prompt)
        sections[key] = prompt[body_start:body_end].strip()
    return sections


def _required_section_keys(context: SpecialistContext | None = None) -> tuple[str, ...]:
    if context is not None and context.role in SPECIALIST_ROLE_IDS:
        return _SPECIALIST_REQUIRED_SECTION_KEYS
    return _BASE_REQUIRED_SECTION_KEYS


_MEANINGLESS_SECTION_RE = re.compile(
    r"^\s*(?:n/?a|none|tbd|todo|placeholder|same as above|see above|\.{3}|-+\s*)\s*$",
    re.IGNORECASE,
)


def _section_nonempty(body: str, *, key: str) -> bool:
    text = body.strip()
    if not text:
        return False
    if _MEANINGLESS_SECTION_RE.match(text):
        return False
    if key == "ownership_boundaries":
        return "### Owned by this specialist" in text and "### Requires handoff" in text
    if key == "assigned_specialist":
        return "- Role:" in text and "- Workspace:" in text
    if key == "steps":
        numbered = [line for line in text.splitlines() if re.match(r"^\s*\d+[\).\s]", line.strip())]
        return len(numbered) >= _MIN_STEP_LINES
    if key in {
        "delivery_mode",
        "in_scope",
        "out_of_scope",
        "acceptance_criteria",
        "validation",
        "handoff",
        "constraints",
        "assumptions",
    }:
        return any(line.strip().startswith("-") for line in text.splitlines())
    return len(text) >= 12


def _assigned_role_matches(sections: dict[str, str], context: SpecialistContext | None) -> bool:
    if context is None or context.role not in SPECIALIST_ROLE_IDS:
        return True
    assigned = sections.get("assigned_specialist", "")
    display = context.profile.display_name
    return bool(re.search(rf"\bRole:\s*{re.escape(display)}\b", assigned, re.IGNORECASE))


def instructions_markdown_is_complete(
    prompt: str,
    context: SpecialistContext | None = None,
) -> bool:
    extracted = extract_instructions_markdown(prompt)
    if not extracted:
        return False
    sections = _parse_sections(extracted)
    if not _assigned_role_matches(sections, context):
        return False
    for key in _required_section_keys(context):
        if not _section_nonempty(sections.get(key, ""), key=key):
            return False
    return True


def _summarize_goal(source: str) -> str:
    cleaned = re.sub(r"\s+", " ", source.strip())
    if not cleaned:
        return "Complete the operator request."
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0].strip()
    if len(first_sentence) >= 24:
        return first_sentence
    return cleaned[:220].rstrip(" ,.;") + ("…" if len(cleaned) > 220 else "")


def _infer_scope_bullets(source: str, context: SpecialistContext | None = None) -> list[str]:
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
    if context is not None and context.role in SPECIALIST_ROLE_IDS:
        profile = context.profile
        role_items = [
            f"{profile.display_name} owned work: {item}"
            for item in profile.primary_responsibilities[:2]
        ]
        candidates = role_items + candidates
    return candidates[:8]


def _infer_steps(source: str, context: SpecialistContext | None = None) -> list[str]:
    bullets = _infer_scope_bullets(source, context)
    role = context.role if context is not None else GENERAL_ROLE_ID
    steps = [
        "Read the source request and restate the Goal, acceptance checks, and anything explicitly out of scope.",
        "Confirm role ownership and workspace scope before changing anything.",
    ]
    if role == "lead":
        steps.append("Decompose implementation work into owned specialist tasks with sequence, dependencies, and evidence requirements.")
    elif role == "watcher":
        steps.append("Reproduce or inspect the reported behaviour read-only and capture expected-versus-actual evidence.")
    elif role == "frontend":
        steps.append("Inspect the relevant client routes, components, state, responsive layout, and visible error/loading states.")
    elif role == "backend":
        steps.append("Inspect the relevant server routes, persistence, authorization, schemas, jobs, and failure paths.")
    elif role == "integrations":
        steps.append("Inspect the relevant external API, auth, webhook, callback, mapping, retry, and secret-boundary contracts.")
    else:
        steps.append("Map the requested product areas to concrete screens, roles, and workflows before changing anything.")
    for bullet in bullets[:4]:
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


def _infer_context(source: str, context: SpecialistContext | None = None) -> str:
    lowered = source.lower()
    if context is not None and context.role == GENERAL_ROLE_ID:
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


def _infer_delivery_mode_bullets(source: str, context: SpecialistContext | None = None) -> list[str]:
    lowered = source.lower()
    if context is not None and context.role in SPECIALIST_ROLE_IDS:
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


def _infer_acceptance_criteria(source: str, context: SpecialistContext | None = None) -> list[str]:
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
    if context is not None and context.role in SPECIALIST_ROLE_IDS:
        criteria.extend(context.profile.required_evidence[:3])
    return criteria


def _infer_validation_bullets(source: str, context: SpecialistContext | None = None) -> list[str]:
    lowered = source.lower()
    bullets = [
        "Run the narrowest local validation command that covers the changed path.",
        "If no automated test exists, perform a manual smoke check and record exactly what was checked.",
    ]
    if context is not None and context.role in SPECIALIST_ROLE_IDS:
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
    return [
        "### Owned by this specialist",
        *owned,
        "",
        "### Requires handoff",
        *handoffs,
    ]


def _handoff_bullets(context: SpecialistContext | None = None) -> list[str]:
    if context is None or context.role == GENERAL_ROLE_ID:
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


def build_instructions_markdown_from_source(
    source: str,
    context: SpecialistContext | None = None,
) -> str:
    cleaned = source.strip()
    context = context or SpecialistContext(role=GENERAL_ROLE_ID)
    profile = role_profile(context.role)
    goal = _summarize_goal(cleaned)
    context_text = _infer_context(cleaned, context)
    delivery_mode = _infer_delivery_mode_bullets(cleaned, context)
    in_scope = _infer_scope_bullets(cleaned, context)
    steps = _infer_steps(cleaned, context)
    acceptance_criteria = _infer_acceptance_criteria(cleaned, context)
    validation = _infer_validation_bullets(cleaned, context)
    out_of_scope = [
        "Committing, pushing, merging, tagging, or releasing unless explicitly requested",
        "Inventing unrelated refactors, migrations, or cleanup chores",
    ]
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
    if prompt_requests_git_actions(cleaned):
        out_of_scope = [item for item in out_of_scope if "Committing" not in item]

    lines = [
        "# Instructions",
        "",
    ]
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
        goal,
        "",
        "## Context",
        context_text,
        "",
        "## Delivery mode",
        *[f"- {item}" for item in delivery_mode],
        "",
        "## In scope",
        *[f"- {item}" for item in in_scope],
        "",
        "## Out of scope",
        *[f"- {item}" for item in out_of_scope],
        "",
        "## Steps",
        *[f"{index}. {step}" for index, step in enumerate(steps, start=1)],
        "",
        "## Acceptance criteria",
        *[f"- {item}" for item in acceptance_criteria],
        "",
        "## Validation",
        *[f"- {item}" for item in validation],
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


def compose_instructions_markdown(
    source: str,
    model_markdown: str | None = None,
    context: SpecialistContext | None = None,
) -> str:
    fallback = build_instructions_markdown_from_source(source, context)
    extracted = extract_instructions_markdown(model_markdown or "")
    if extracted and instructions_markdown_is_complete(extracted, context):
        return extracted if extracted.endswith("\n") else f"{extracted}\n"

    if not extracted or (
        context is not None
        and context.role in SPECIALIST_ROLE_IDS
        and not _assigned_role_matches(_parse_sections(extracted), context)
    ):
        return fallback if fallback.endswith("\n") else f"{fallback}\n"

    model_sections = _parse_sections(extracted)
    fallback_sections = _parse_sections(fallback)
    merged: dict[str, str] = {}
    for key in _required_section_keys(context):
        model_body = model_sections.get(key, "").strip()
        fallback_body = fallback_sections.get(key, "").strip()
        merged[key] = model_body if _section_nonempty(model_body, key=key) else fallback_body

    # Optional sections: keep the model's choice to include or omit them. Only fall back to
    # the deterministic source_request when the required sections above were already
    # incomplete enough to need fallback-filling — a fully-complete model reply that omits
    # these never reaches this branch (see the early return above).
    assumptions = model_sections.get("assumptions", "").strip()
    source_request = model_sections.get("source_request", "").strip()
    handoff = model_sections.get("handoff", "").strip()
    fallback_handoff = fallback_sections.get("handoff", "").strip()
    if not handoff:
        handoff = fallback_handoff
    if not source_request:
        source_request = fallback_sections.get("source_request", "").strip()

    lines = [
        "# Instructions",
        "",
    ]
    if context is not None and context.role in SPECIALIST_ROLE_IDS:
        lines += [
            "## Assigned specialist",
            merged["assigned_specialist"],
            "",
            "## Role mandate",
            merged["role_mandate"],
            "",
            "## Ownership boundaries",
            merged["ownership_boundaries"],
            "",
        ]
    lines += [
        "## Goal",
        merged["goal"],
        "",
        "## Context",
        merged["context"],
        "",
        "## Delivery mode",
        merged["delivery_mode"],
        "",
        "## In scope",
        merged["in_scope"],
        "",
        "## Out of scope",
        merged["out_of_scope"],
        "",
        "## Steps",
        merged["steps"],
        "",
        "## Acceptance criteria",
        merged["acceptance_criteria"],
        "",
        "## Validation",
        merged["validation"],
        "",
    ]
    if handoff:
        lines += ["## Handoff", handoff, ""]
    lines += [
        "## Constraints",
        merged["constraints"],
    ]
    if assumptions:
        lines += ["", "## Assumptions", assumptions]
    if source_request:
        lines += ["", "## Source request", source_request]
    lines.append("")
    return "\n".join(lines)


def instructions_markdown_present(prompt: str) -> bool:
    return extract_instructions_markdown(prompt) is not None


def extract_instructions_markdown(raw: str) -> str | None:
    """Return normalized Instructions markdown when present in model output."""
    text = raw.strip()
    if not text:
        return None

    fence = _FENCED_MARKDOWN_RE.match(text)
    if fence:
        text = fence.group(1).strip()

    if _ALT_INSTRUCTIONS_HEADING_RE.search(text) and not _INSTRUCTIONS_HEADING_RE.search(text):
        text = _ALT_INSTRUCTIONS_HEADING_RE.sub("# Instructions", text, count=1)

    match = _INSTRUCTIONS_HEADING_RE.search(text)
    if not match:
        return None

    extracted = text[match.start() :].strip()
    if "\n---\n" in extracted:
        extracted = extracted.split("\n---\n", 1)[0].strip()

    return extracted if _INSTRUCTIONS_HEADING_RE.match(extracted) else None


def instructions_block_git_actions(prompt: str) -> bool:
    """True when Instructions markdown puts git actions out of scope."""
    if not instructions_markdown_present(prompt):
        return False
    out_of_scope = _parse_sections(prompt).get("out_of_scope", "")
    if not out_of_scope:
        return False
    return bool(_GIT_OUT_OF_SCOPE_RE.search(out_of_scope))


def prompt_requests_git_actions(prompt: str) -> bool:
    """True only for affirmative commit/push intent, not negated mentions."""
    stripped = prompt.strip()
    if not stripped:
        return False
    if instructions_block_git_actions(stripped):
        return False
    if _NEGATED_COMMIT_RE.search(stripped):
        return False
    return bool(_AFFIRMATIVE_COMMIT_RE.search(stripped))
