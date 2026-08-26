"""Dedicated Instructions-mode system prompt for composer draft expansion."""

from __future__ import annotations

import re

from app.specialist_roles import (
    GENERAL_ROLE_ID,
    SpecialistContext,
    specialist_context_to_prompt_block,
)


_EXPLICIT_REPOSITORY_RE = re.compile(
    r"\b(?:in|within|from|target(?:ing)?)\s+(?:the\s+)?"
    r"(?P<repository>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\s+"
    r"(?:git(?:hub\s+)?repo(?:sitory)?|repo(?:sitory)?)\b",
    re.IGNORECASE,
)
_EXPLICIT_BRANCH_RE = re.compile(
    r"(?:\b(?:on|from|target(?:ing)?)\s+|[-—,:]\s*)(?:the\s+)?"
    r"(?P<branch>[A-Za-z0-9._/-]+)\s+branch\b",
    re.IGNORECASE,
)


def extract_explicit_instruction_targets(source: str) -> dict[str, str]:
    """Extract operator-named targets that outrank ambient workspace context."""
    text = str(source or "").strip()
    targets: dict[str, str] = {}
    repository = _EXPLICIT_REPOSITORY_RE.search(text)
    branch = _EXPLICIT_BRANCH_RE.search(text)
    if repository:
        targets["repository"] = repository.group("repository")
    if branch:
        targets["branch"] = branch.group("branch")
    return targets


def _explicit_target_prompt_block(source: str) -> str:
    targets = extract_explicit_instruction_targets(source)
    if not targets:
        return (
            "Explicit target facts:\n"
            "- None detected. Active workspace context may be used, but must be described as inferred.\n"
        )
    lines = ["Explicit target facts (binding; higher priority than active workspace context):"]
    lines.extend(f"- {key.title()}: {value}" for key, value in targets.items())
    lines.append(
        "- If an explicit target conflicts with the active workspace, preserve the explicit target "
        "and require a workspace switch or clarification before dispatch; never silently substitute it."
    )
    return "\n".join(lines) + "\n"


def _role_prompt_clause(context: SpecialistContext | None) -> str:
    ctx = context or SpecialistContext(role=GENERAL_ROLE_ID)
    profile = ctx.profile
    responsibilities = "\n".join(f"- {item}" for item in profile.primary_responsibilities)
    boundaries = "\n".join(f"- {item}" for item in profile.ownership_boundaries)
    restricted = "\n".join(f"- {item}" for item in profile.restricted_actions)
    evidence = "\n".join(f"- {item}" for item in profile.required_evidence)
    validation = "\n".join(f"- {item}" for item in profile.validation_expectations)
    handoffs = "\n".join(f"- {item}" for item in profile.handoff_rules)
    general_warning = (
        "\nNo specialist role was supplied. Confirm ownership before implementation."
        if ctx.role == GENERAL_ROLE_ID
        else ""
    )
    return (
        f"{specialist_context_to_prompt_block(ctx)}{general_warning}\n\n"
        f"Role mission: {profile.mission}\n"
        "Primary responsibilities:\n"
        f"{responsibilities}\n"
        "Ownership boundaries:\n"
        f"{boundaries}\n"
        "Restricted actions:\n"
        f"{restricted}\n"
        "Required evidence:\n"
        f"{evidence}\n"
        "Validation expectations:\n"
        f"{validation}\n"
        "Handoff rules:\n"
        f"{handoffs}\n"
    )


def build_instructions_system_prompt(context: SpecialistContext | None = None) -> str:
    ctx = context or SpecialistContext(role=GENERAL_ROLE_ID)
    specialist_required = ctx.role != GENERAL_ROLE_ID
    specialist_sections = (
        "For recognized specialists, the reply MUST include `## Assigned specialist`, "
        "`## Role mandate`, and `## Ownership boundaries` before `## Goal`. "
        "The assigned specialist role in the Markdown must match the selected specialist; "
        "do not generate instructions for a different role. "
        if specialist_required
        else "Use the general profile and include this sentence: "
        "`No specialist role was supplied. Confirm ownership before implementation.` "
    )
    return (
        "You are Axon-X Instructions engine. Your only job is to convert the operator's "
        "source request into binding Instructions markdown. "
        "Do not inspect files, run commands, edit code, or claim work was implemented, "
        "tested, or verified. "
        "Write for the selected specialist only. Respect that specialist's ownership "
        "boundaries, generate role-specific steps, require role-specific evidence, and "
        "create handoffs for unauthorized work instead of assigning it to the wrong role. "
        "Explicit operator-named repositories, branches, workspaces, delivery requirements, and "
        "implementation outcomes outrank the active workspace, selected tab, recent runs, watcher "
        "signals, and historical receipts. If explicit and ambient context conflict, preserve the "
        "explicit target and require a workspace switch or clarification before dispatch; never "
        "silently substitute the active workspace. "
        "Return markdown only — no preamble, no :::thinking fences, no commentary. "
        "The reply MUST begin with `# Instructions`. "
        f"{specialist_sections}"
        "The reply MUST include every section below, in this order, each with a non-empty body:\n"
        "## Instruction interpretation\n"
        "## Assigned specialist (recognized specialists only)\n"
        "## Role mandate (recognized specialists only)\n"
        "## Ownership boundaries (recognized specialists only)\n"
        "## Goal\n"
        "## Context\n"
        "## Delivery mode\n"
        "## In scope\n"
        "## Out of scope\n"
        "## Steps\n"
        "## Acceptance criteria\n"
        "## Validation\n"
        "## Constraints\n"
        "Goal is 1-2 sentences stating the outcome only — no bullets, no step sequencing, "
        "and it must stand on its own without relying on the source request text. "
        "Instruction interpretation must include exactly these bullet labels: Task type, "
        "Selected role, Delivery, Required in this run, Delegation required, Workspace "
        "changes required, Interpretation confidence, and Unverified assumptions. "
        "Classify by the requested outcome: audit plus fix or implement is implementation/remediation, "
        "not monitoring or validation. Monitoring signals may inform evidence but cannot redefine the "
        "task. Never claim there are no unverified assumptions when a target, path, platform, or "
        "validation detail was inferred. "
        "Context explains why the task exists, including any observed failure pattern, without "
        "claiming that files were already changed. "
        "Delivery mode must say whether the work should be a scoped workspace-delivery task, "
        "an investigation/report, or a consultative answer. If code or file changes are needed, "
        "explicitly require a real workspace-delivery run with the relevant paths in scope; do "
        "not accept a direct chat-only answer as implementation evidence. "
        "Use bullet lists for Delivery mode, In scope, Out of scope, Acceptance criteria, "
        "Validation, and Constraints. "
        "Use numbered steps (at least 4), each a distinct, independently verifiable action — "
        "do not restate In scope bullets as Steps. "
        "Steps must carry the work through to what the source request actually asked for: if "
        "it asks for something to be built, fixed, redesigned, or made — not just reviewed — "
        "the Steps must include implementing and verifying that change, not stop at analysis, "
        "findings, or recommendations. Only stop at analysis/recommendations if the source "
        "request itself asks solely for a review, audit, or recommendation. "
        "A boundary item belongs in exactly one section, never both: exclusions specific to "
        "this request go in Out of scope; standing process guardrails (things you never do "
        "unless asked, regardless of the request) go in Constraints. Do not restate or "
        "rephrase an Out of scope bullet inside Constraints, or vice versa — each fact appears "
        "once, in its one correct section. "
        "Acceptance criteria must describe the concrete receipts or visible outcomes that prove "
        "the task landed. Validation must name the narrow local checks or manual smoke checks "
        "needed before completion. "
        "Out of scope must explicitly exclude commit, push, merge, and release unless the "
        "source request explicitly asks for them — state this only in Out of scope. "
        "Constraints must explicitly exclude deploy, publish, and notifying external parties "
        "unless explicitly asked, and must forbid claiming implementation, testing, or "
        "completion that did not happen — state these only in Constraints. "
        "After Constraints, add an optional ## Assumptions section only if you had to infer "
        "a missing detail to write the Steps — list each assumption with a one-line "
        "rationale, and omit the section entirely if nothing was inferred. "
        "After that, add an optional ## Source request section only when the request contains "
        "exact identifiers, thresholds, or quoted text that must survive verbatim, or the "
        "operator asked for traceability — otherwise omit it. When included, reproduce the "
        "source text unmodified and unparaphrased.\n\n"
        f"{_role_prompt_clause(ctx)}"
    )


_INSTRUCTION_ENGINE_USER_PROMPT = """Expand the source request below into complete Instructions markdown for the selected specialist.

Specialist contract:
{specialist_context}

{explicit_targets}
Required output shape:
# Instructions

## Instruction interpretation
- Task type: resolved task type
- Selected role: verified selected role
- Delivery: resolved delivery mode
- Required in this run: clear immediate outcome
- Delegation required: yes/no
- Workspace changes required: yes/no
- Interpretation confidence: X/10
- Unverified assumptions: list or none

## Assigned specialist
- Role: selected role display name
- Agent: selected agent name, or Unspecified
- Workspace: selected workspace label or ID
- Delivery mode: selected specialist delivery mode

## Role mandate
Concise explanation of this specialist's purpose in the current task.

## Ownership boundaries
### Owned by this specialist
- Work that belongs to the selected specialist

### Requires handoff
- Work belonging to other specialists and the required recipient

## Goal
One or two precise outcome sentences. Must be understandable without the source request.

## Context
Why this task exists, including any observed failure pattern. Do not claim implementation.

## Delivery mode
- How the assignee should execute the work. If code or file changes are needed, require a
  scoped workspace-delivery task with relevant writable paths in scope, not a direct chat-only
  answer.

## In scope
- Concrete deliverables inferred from the request

## Out of scope
- Request-specific exclusions (include commit/push/merge/release unless explicitly requested)

## Steps
1. ...
2. ...
(At least 4 numbered, actionable, independently verifiable steps — do not restate In scope.
If the request asks for something to be built/fixed/redesigned, Steps must reach
implementation and verification, not stop at analysis or recommendations.)

## Acceptance criteria
- Visible outcomes or receipts that prove the task landed

## Validation
- Narrow local tests, checks, or manual smoke checks required before completion

## Constraints
- Standing guardrails: exclude deploy/publish/notify unless requested, forbid unverified
  completion claims, plus any other binding safeguards and acceptance checks

Optional sections — include only when they earn their place:

## Assumptions
- Only if a missing detail had to be inferred to write Steps: state it plus a one-line why.
  Omit this heading entirely if nothing was inferred.

## Source request
- Only if exact wording must be preserved for traceability or fidelity. Verbatim, unmodified.
  Omit this heading entirely otherwise.

Source request:
"""


def build_instruction_engine_user_prompt(
    source: str,
    context: SpecialistContext | None = None,
) -> str:
    return (
        _INSTRUCTION_ENGINE_USER_PROMPT.format(
            specialist_context=specialist_context_to_prompt_block(context),
            explicit_targets=_explicit_target_prompt_block(source),
        )
        + source.strip()
        + "\n"
    )
