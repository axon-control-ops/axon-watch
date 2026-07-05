# ADR-001: Build Axon-Watch In A New Repo

## Status

Accepted

## Context

The current `axon-local` repository contains valuable product concepts and
working slices, but it also carries significant historical complexity, hotspot
files, and architectural baggage.

The new integrated product needs:

- a cleaner service boundary
- a cleaner frontend foundation
- a single source of truth for contracts and ownership
- a controlled import policy instead of wholesale inheritance

## Decision

Build the new product in a new repository:

- `/home/edp/axon-nvme/repos/axon-watch`

Treat the current `axon-local` repo as a donor/reference codebase, not the
implementation base.

## Alternatives Considered

### Continue directly inside `axon-local`

Rejected because the new product needs cleaner boundaries, a cleaner frontend
foundation, and a stricter one-source-of-truth structure than the current repo
can provide without heavy transitional noise.

### Hybrid approach with a long-lived in-repo prototype folder

Rejected because it risks creating a second monolith or an unwired prototype
inside the legacy repo rather than a clean new source of truth.

## Trade-Offs

- Gains a cleaner starting point and stronger ownership boundaries
- Costs more up-front setup and deliberate migration work
- Reduces inherited complexity
- Increases short-term duplication during transition

## Consequences

### Positive

- clearer architecture from day one
- easier enforcement of ownership boundaries
- less accidental inheritance of monolith patterns
- cleaner onboarding and documentation

### Negative

- some useful behavior must be reimplemented instead of edited in place
- short-term duplication during the transition
- import discipline is required to avoid drift

## Reevaluation Triggers

Reevaluate this ADR if:

- the new repo causes unacceptable delivery drag without offsetting clarity
- a shared mono-repo structure becomes clearly superior for tooling or governance
- the migration seam proves impossible to manage cleanly across two repos
