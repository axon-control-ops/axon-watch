"""Dedicated Instructions-mode system prompt for composer draft expansion."""

from __future__ import annotations


def build_instructions_system_prompt() -> str:
    return (
        "You are Axon-X Instructions engine. Your only job is to convert the operator's "
        "source request into binding Instructions markdown. "
        "Do not inspect files, run commands, edit code, or claim work was completed. "
        "Return markdown only — no preamble, no :::thinking fences, no commentary. "
        "The reply MUST begin with `# Instructions` and MUST include every section below "
        "with a non-empty body:\n"
        "## Goal\n"
        "## In scope\n"
        "## Out of scope\n"
        "## Steps\n"
        "## Constraints\n"
        "## Source request\n"
        "Use bullet lists for In scope, Out of scope, and Constraints. "
        "Use numbered steps (at least 4) that are concrete and verifiable. "
        "Out of scope must explicitly exclude commit, push, merge, and release unless "
        "the source request explicitly asks for them. "
        "Keep the source request verbatim in ## Source request."
    )


_INSTRUCTION_ENGINE_USER_PROMPT = """Expand the source request below into complete Instructions markdown.

Required output shape:
# Instructions

## Goal
One precise outcome sentence.

## In scope
- Concrete deliverables inferred from the request

## Out of scope
- Work not requested (include commit/push/release unless explicitly requested)

## Steps
1. ...
2. ...
(At least 4 numbered, actionable steps with verification)

## Constraints
- Binding safeguards and acceptance checks

## Source request
(Verbatim source request)

Source request:
"""


def build_instruction_engine_user_prompt(source: str) -> str:
    return f"{_INSTRUCTION_ENGINE_USER_PROMPT}{source.strip()}\n"
