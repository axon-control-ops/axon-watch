# Axon-Watch ADR Governance

## Purpose

This document defines how architecture decision records (ADRs) are created,
maintained, and superseded for the new `axon-watch` project.

## Core Rule

Accepted ADRs are part of the project source of truth.

They must be:

- numbered
- immutable
- superseded by new ADRs instead of materially edited
- explicit about alternatives considered
- explicit about trade-offs
- explicit about reevaluation triggers

## Lifecycle

### 1. Proposed

An ADR may begin as proposed while a major decision is still open.

### 2. Accepted

Once accepted, the ADR becomes an immutable decision record.

Allowed edits after acceptance:

- typo fixes
- formatting fixes
- links to superseding ADRs
- metadata clarifications that do not change the decision

Disallowed edits after acceptance:

- changing the decision itself
- changing the trade-off analysis materially
- changing the chosen alternative without creating a new ADR

### 3. Superseded

If a decision changes, create a new ADR and mark the old one as superseded.

Do not rewrite history by silently editing the accepted ADR.

## Required Sections

Every ADR must include:

1. `Status`
2. `Context`
3. `Decision`
4. `Alternatives Considered`
5. `Trade-Offs`
6. `Consequences`
7. `Reevaluation Triggers`

## Numbering Rule

Use sequential numbering:

- `ADR-001-*`
- `ADR-002-*`
- `ADR-003-*`

Numbers should never be reused.

## Immutability Rule

The purpose of an ADR is to preserve the reasoning that led to a decision at a
point in time.

If the reasoning changes enough to change the decision, the project needs a new
ADR, not a rewritten old one.

## Supersession Rule

When superseding an ADR:

- the new ADR must explicitly name the old one
- the old ADR should be updated only to note that it is superseded
- the original decision content should remain intact

## Alternatives Rule

Alternatives considered must be real alternatives, not placeholders.

Each ADR should record:

- what other option(s) were considered
- why they were not chosen

## Trade-Off Rule

Every accepted ADR should capture both:

- what the decision improves
- what the decision makes harder, slower, riskier, or more constrained

## Reevaluation Triggers

Each ADR must state the conditions that would justify reconsidering the
decision.

Examples:

- changed scale assumptions
- changed deployment model
- persistent performance failure
- unacceptable delivery complexity
- new verified constraints from real usage

## Source Control Rule

ADRs should live in source control with the rest of the planning and later repo
docs so decisions are visible and reviewable.

## Acceptance Criteria

ADR governance is being followed when:

- accepted ADRs are stable and numbered
- changed decisions create new ADRs instead of rewritten old ones
- readers can understand the alternatives, trade-offs, and reconsideration conditions
