# ADR-004: Use Explicit Persisted Execution State

## Status

Accepted

## Context

The product needs long-running, pausable, approval-aware, review-aware work that
remains trustworthy across restarts and across multiple UI surfaces.

Pure prompt-driven ReAct is useful as a reasoning technique, but it is not a
sufficient source of truth for:

- run phases
- stop/resume behavior
- approval boundaries
- review-ready state
- resumability

## Decision

Use:

- explicit persisted run records
- structured tool/function calling
- canonical run phases and transition rules
- resumable execution history

ReAct-style reasoning may still be used inside bounded planning or execution
steps, but it must not be the primary system truth.

## Alternatives Considered

### Use pure prompt-driven ReAct as the primary execution source of truth

Rejected because it does not provide sufficiently explicit, durable, cross-surface
state for stop/resume/approval/review behavior.

### Use only ad hoc job rows without a canonical phase model

Rejected because the product needs explicit shared semantics, not only generic
task records.

## Trade-Offs

- Gains trust and consistency across run surfaces
- Costs more up-front modeling and persistence discipline
- Improves resumability and later durable orchestration options
- Reduces the simplicity of prompt-only experimentation

## Consequences

### Positive

- consistent run-state across all surfaces
- reliable stop/resume/approval semantics
- easier later adoption of durable orchestration if needed

### Negative

- requires more up-front modeling than prompt-only flows
- more DTO and persistence design work
- stricter discipline around transitions and receipts

## Reevaluation Triggers

Reevaluate this ADR if:

- the explicit phase model proves too rigid for real user workflows
- a durable orchestration platform becomes necessary and materially changes the state model
- the transition cost of the current model outweighs its trust benefits
