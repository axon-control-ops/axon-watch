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
2. **Out of scope is binding.** If they did not ask for commit / push / merge / release, do not add those steps.
3. Prefer the product helper when available: composer **Instructions** button, or
   `apps/console-web/src/lib/plain-text-to-instructions.ts`.
4. Then execute only the listed steps.
5. Reply with a short summary of what changed.

## Output shape

```markdown
# Instructions

## Goal
One sentence outcome.

## In scope
- …

## Out of scope
- Any task that was not asked for

## Steps
1. …
2. …

## Constraints
- Follow only the steps listed above
- Do not invent tasks that were not asked for
```

## Do not

- Invent “clear the desk” / commit chores
- Expand into unrelated refactors
- Soften or drop an explicit “do not …” constraint
