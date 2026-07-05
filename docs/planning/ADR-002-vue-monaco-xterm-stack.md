# ADR-002: Use Vue, Pinia, Monaco, And xterm.js

## Status

Accepted

## Context

The new product is not a light progressive-enhancement shell. It is an
IDE-grade integrated application with:

- multiple coordinated panels
- explicit shared state
- editor and terminal surfaces
- agent dock behavior
- operator dashboard and signal surfaces

The current Alpine-style approach is useful for enhancement scenarios, but it is
not the best long-term fit for this class of application.

## Decision

Use:

- Vue 3
- TypeScript
- Pinia
- Monaco Editor
- xterm.js

## Alternatives Considered

### Continue with Alpine-style progressive enhancement

Rejected because the new product is an IDE-grade application with shared state,
multiple coordinated panels, and richer long-lived UI behavior.

### Use a different frontend stack such as React

Not chosen at this stage because Vue + Pinia provides a strong component and
state model with a simpler path toward the planned shell structure and explicit
state contracts.

## Trade-Offs

- Gains stronger component boundaries and explicit state management
- Costs a fuller frontend toolchain and reimplementation effort
- Gains Monaco/xterm alignment with IDE-class UX
- Reduces direct reuse of the current UI implementation approach

## Consequences

### Positive

- component boundaries suited to a large application
- explicit shared state
- stronger typing and contract reuse
- native-feeling editor and terminal building blocks

### Negative

- requires a fuller frontend toolchain
- reimplementation cost versus copy-pasting current UI logic
- team discipline needed around shared stores and DTOs

## Reevaluation Triggers

Reevaluate this ADR if:

- the chosen stack fails to support the integrated shell cleanly
- performance or developer-experience costs are consistently unacceptable
- another stack becomes materially better aligned with the documented product needs
