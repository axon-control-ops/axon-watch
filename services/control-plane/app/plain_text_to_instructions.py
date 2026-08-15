"""Parse Instructions markdown and detect binding out-of-scope git gates."""

from __future__ import annotations

import re

_INSTRUCTIONS_HEADING_RE = re.compile(r"^#\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_ALT_INSTRUCTIONS_HEADING_RE = re.compile(r"^##\s*Instructions\b", re.IGNORECASE | re.MULTILINE)
_FENCED_MARKDOWN_RE = re.compile(
    r"^```(?:markdown|md)?\s*\r?\n([\s\S]*?)\r?\n```\s*$",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(
    r"^##\s*(Goal|In scope|Out of scope|Steps|Constraints|Assumptions|Source request)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_REQUIRED_SECTION_KEYS = ("goal", "in_scope", "out_of_scope", "steps", "constraints")
_OPTIONAL_SECTION_KEYS = ("assumptions", "source_request")
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


def _section_nonempty(body: str, *, key: str) -> bool:
    text = body.strip()
    if not text:
        return False
    if key == "steps":
        numbered = [line for line in text.splitlines() if re.match(r"^\s*\d+[\).\s]", line.strip())]
        return len(numbered) >= _MIN_STEP_LINES
    if key in {"in_scope", "out_of_scope", "constraints", "assumptions"}:
        return any(line.strip().startswith("-") for line in text.splitlines())
    return len(text) >= 12


def instructions_markdown_is_complete(prompt: str) -> bool:
    extracted = extract_instructions_markdown(prompt)
    if not extracted:
        return False
    sections = _parse_sections(extracted)
    for key in _REQUIRED_SECTION_KEYS:
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


def _infer_scope_bullets(source: str) -> list[str]:
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
    return candidates[:8]


def _infer_steps(source: str) -> list[str]:
    bullets = _infer_scope_bullets(source)
    steps = [
        "Read the source request and restate the Goal, acceptance checks, and anything explicitly out of scope.",
        "Map the requested product areas to concrete screens, roles, and workflows in the workspace app before changing anything.",
    ]
    for bullet in bullets[:4]:
        steps.append(f"Exercise and document: {bullet}. Capture screenshots, broken flows, and missing capabilities.")
    steps.extend(
        [
            "When Axon-X or the product fleet is part of the request, run the work through that workflow and record fixes or upgrades discovered.",
            "Verify the requested outcomes on web and mobile where applicable; note any feature that requires a native rebuild instead of OTA.",
            "Summarize findings, remaining gaps, and the next operator action without claiming git/release work that was not requested.",
        ]
    )
    return steps[:8]


def build_instructions_markdown_from_source(source: str) -> str:
    cleaned = source.strip()
    goal = _summarize_goal(cleaned)
    in_scope = _infer_scope_bullets(cleaned)
    steps = _infer_steps(cleaned)
    out_of_scope = [
        "Committing, pushing, merging, tagging, or releasing unless explicitly requested",
        "Inventing unrelated refactors, migrations, or cleanup chores",
    ]
    constraints = [
        "Follow only the steps listed above",
        "Treat Out of scope as binding",
        "Preserve every explicit requirement from the source request",
        "Call out native-build-only gaps separately from OTA-safe fixes",
        "Do not deploy, publish, or notify external parties unless explicitly requested",
        "Do not claim work was implemented, tested, or verified without evidence",
    ]
    if prompt_requests_git_actions(cleaned):
        out_of_scope = [item for item in out_of_scope if "Committing" not in item]

    lines = [
        "# Instructions",
        "",
        "## Goal",
        goal,
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
        "## Constraints",
        *[f"- {item}" for item in constraints],
        "",
        "## Source request",
        cleaned,
        "",
    ]
    return "\n".join(lines)


def compose_instructions_markdown(source: str, model_markdown: str | None = None) -> str:
    fallback = build_instructions_markdown_from_source(source)
    extracted = extract_instructions_markdown(model_markdown or "")
    if extracted and instructions_markdown_is_complete(extracted):
        return extracted if extracted.endswith("\n") else f"{extracted}\n"

    if not extracted:
        return fallback if fallback.endswith("\n") else f"{fallback}\n"

    model_sections = _parse_sections(extracted)
    fallback_sections = _parse_sections(fallback)
    merged: dict[str, str] = {}
    for key in _REQUIRED_SECTION_KEYS:
        model_body = model_sections.get(key, "").strip()
        fallback_body = fallback_sections.get(key, "").strip()
        merged[key] = model_body if _section_nonempty(model_body, key=key) else fallback_body

    # Optional sections: keep the model's choice to include or omit them. Only fall back to
    # the deterministic source_request when the required sections above were already
    # incomplete enough to need fallback-filling — a fully-complete model reply that omits
    # these never reaches this branch (see the early return above).
    assumptions = model_sections.get("assumptions", "").strip()
    source_request = model_sections.get("source_request", "").strip()
    if not source_request:
        source_request = fallback_sections.get("source_request", "").strip()

    lines = [
        "# Instructions",
        "",
        "## Goal",
        merged["goal"],
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
