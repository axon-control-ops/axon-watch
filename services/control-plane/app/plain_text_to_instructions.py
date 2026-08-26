"""Parse Instructions markdown and detect binding out-of-scope git gates."""

from __future__ import annotations

import re

from app.specialist_roles import (
    GENERAL_ROLE_ID,
    SPECIALIST_ROLE_IDS,
    SpecialistContext,
)
from app.instructions_engine import extract_explicit_instruction_targets
from app.instructions_fallback_builder import (
    build_fallback_instructions_markdown,
    infer_instruction_task_type,
    infer_unverified_instruction_assumptions,
)

_INSTRUCTIONS_HEADING_RE = re.compile(r"^#\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_ALT_INSTRUCTIONS_HEADING_RE = re.compile(r"^##\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_FENCED_MARKDOWN_RE = re.compile(
    r"^```(?:markdown|md)?\s*\r?\n([\s\S]*?)\r?\n```\s*$",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(
    r"^##\s*(Instruction interpretation|Assigned specialist|Role mandate|Ownership boundaries|Goal|Context|Delivery mode|In scope|Out of scope|Steps|Acceptance criteria|Validation|Handoff|Constraints|Assumptions|Source request)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_BASE_REQUIRED_SECTION_KEYS = (
    "instruction_interpretation",
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
    if key == "instruction_interpretation":
        required = (
            "- Task type:",
            "- Selected role:",
            "- Delivery:",
            "- Required in this run:",
            "- Delegation required:",
            "- Workspace changes required:",
            "- Interpretation confidence:",
            "- Unverified assumptions:",
        )
        return all(item in text for item in required)
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


def build_instructions_markdown_from_source(
    source: str,
    context: SpecialistContext | None = None,
) -> str:
    return build_fallback_instructions_markdown(
        source,
        context,
        git_actions_requested=prompt_requests_git_actions(source),
    )


def _replace_interpretation_bullet(markdown: str, label: str, value: str) -> str:
    pattern = re.compile(
        rf"^-\s*{re.escape(label)}:\s*.*$",
        re.IGNORECASE | re.MULTILINE,
    )
    replacement = f"- {label}: {value}"
    if pattern.search(markdown):
        return pattern.sub(replacement, markdown, count=1)
    return markdown


def _normalize_instruction_facts(
    markdown: str,
    source: str,
    context: SpecialistContext | None,
) -> str:
    """Enforce source-derived facts after model generation.

    Model choice may improve wording, but cannot override task type, explicit
    targets, truthful assumptions, or repository-relevant constraints.
    """
    ctx = context or SpecialistContext(role=GENERAL_ROLE_ID)
    normalized = _replace_interpretation_bullet(
        markdown,
        "Task type",
        infer_instruction_task_type(source, ctx),
    )
    assumptions = infer_unverified_instruction_assumptions(source, ctx)
    targets = extract_explicit_instruction_targets(source)
    explicit_repository = targets.get("repository")
    ambient_workspace = (ctx.workspace_label or ctx.workspace_id or "").strip()
    if (
        explicit_repository
        and ambient_workspace
        and explicit_repository.lower().replace("_", "-")
        not in ambient_workspace.lower().replace("_", "-")
    ):
        conflict = (
            f"explicit repository {explicit_repository} differs from active workspace "
            f"{ambient_workspace}; verify access and switch workspace before dispatch"
        )
        assumptions = conflict if assumptions == "none" else f"{assumptions}; {conflict}"
    normalized = _replace_interpretation_bullet(
        normalized,
        "Unverified assumptions",
        assumptions,
    )
    if explicit_repository:
        assigned = _parse_sections(normalized).get("assigned_specialist", "")
        if assigned:
            updated = re.sub(
                r"^-\s*Workspace:\s*.*$",
                f"- Workspace: {explicit_repository}",
                assigned,
                count=1,
                flags=re.IGNORECASE | re.MULTILINE,
            )
            normalized = normalized.replace(assigned, updated, 1)

    normalized = re.sub(
        r"^-\s*Follow only the steps listed above\s*$",
        (
            "- Follow the required objectives and safety boundaries; add evidence-based "
            "diagnostic steps when necessary and record why they were added"
        ),
        normalized,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    repository_mentions_mobile = any(
        token in source.lower() for token in ("native", "mobile", "ota", "android", "ios")
    )
    if not repository_mentions_mobile:
        normalized = re.sub(
            r"^-\s*Call out native-build-only gaps separately from OTA-safe fixes\s*\n?",
            "",
            normalized,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    if ctx.role == "lead":
        normalized = normalized.replace(
            "- Log, reproduce, and fix defects encountered during holistic testing",
            (
                "- Coordinate defect reproduction, assign confirmed fixes to owning specialists, "
                "and review their implementation evidence"
            ),
        )
    return normalized


def compose_instructions_markdown(
    source: str,
    model_markdown: str | None = None,
    context: SpecialistContext | None = None,
) -> str:
    fallback = build_instructions_markdown_from_source(source, context)
    extracted = extract_instructions_markdown(model_markdown or "")
    if extracted and instructions_markdown_is_complete(extracted, context):
        normalized = _normalize_instruction_facts(extracted, source, context)
        return normalized if normalized.endswith("\n") else f"{normalized}\n"

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
        "## Instruction interpretation",
        merged["instruction_interpretation"],
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
    return _normalize_instruction_facts("\n".join(lines), source, context)


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
