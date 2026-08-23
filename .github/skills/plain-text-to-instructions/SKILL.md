---
name: plain-text-to-instructions
description: >-
  Convert a plain-language request into concise Instructions markdown with Goal,
  In scope, Out of scope, Steps, and Constraints. Use when the request is messy,
  multi-part, or easy to over-interpret (for example inventing commits).
---

# Plain text → Instructions

## When to use

- Before acting on a loose or emotional request
- When the asker is correcting a previous misread
- When multiple jobs are mixed in one paragraph

## Rules

1. Convert the request into Instructions markdown first.
2. **Out of scope is binding** for request-specific exclusions — if they did not ask for
   commit / push / merge / release, do not add those steps.
3. **Constraints is binding** for standing process guardrails (deploy/publish/notify unless
   asked, no unverified completion claims) — do not duplicate these into Out of scope.
4. Prefer the product helper when available: composer **Instructions** button, backed by
   `services/control-plane/app/instructions_engine.py` (prompt) and
   `services/control-plane/app/plain_text_to_instructions.py` (parsing/fallback).
5. Then execute only the listed steps.
6. Reply with a short summary of what changed.

## Output shape

```markdown
# Instructions

## Goal
One or two sentence outcome — must stand on its own, no bullets.

## In scope
- …

## Out of scope
- Request-specific exclusion (any task that was not asked for)

## Steps
1. …
2. …
(at least 4, each independently verifiable — don't restate In scope)

## Constraints
- Follow only the steps listed above
- Do not invent tasks that were not asked for
- Do not deploy, publish, or notify external parties unless explicitly requested
- Do not claim work was implemented, tested, or verified without evidence

## Assumptions
(optional — include only if a missing detail had to be inferred; state it plus why;
omit the whole heading if nothing was inferred)

## Source request
(optional — include only when exact wording must be preserved for traceability or
fidelity; verbatim and unmodified; omit the whole heading otherwise)
```

## Do not

- Invent "clear the desk" / commit chores
- Expand into unrelated refactors
- Soften or drop an explicit "do not …" constraint
- Pad the document with Assumptions or Source request when neither earns its place
