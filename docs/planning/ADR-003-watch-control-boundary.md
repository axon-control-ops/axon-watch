# ADR-003: Separate Axon-Watch From The Control Plane

## Status

Accepted

## Context

The current product shape mixes always-on monitoring work with interactive
control-plane behavior in ways that increase startup weight and runtime pressure.

The new product needs:

- independent monitoring continuity
- lighter interactive runtime behavior
- a clear ownership split for signals, approvals, and action execution

## Decision

Split the backend into:

- `services/axon-watch`
- `services/control-plane`

Boundary rule:

```text
Watch detects and persists.
Control plane decides and acts.
```

## Alternatives Considered

### Keep monitoring inside the interactive control-plane process

Rejected because it recreates the same process-weight and lifecycle coupling the
new product is trying to escape.

### Split into more than two services immediately

Rejected for phase 1 because it would add deployment and contract complexity
before the core watch/control seam is proven.

## Trade-Offs

- Gains restart isolation and cleaner ownership
- Costs more service-to-service contract design
- Improves dedicated-server portability
- Adds operational and observability surfaces to manage

## Consequences

### Positive

- monitoring can remain continuous through control-plane restarts
- easier dedicated-server portability
- clearer contracts and failure boundaries

### Negative

- service-to-service contracts must be designed carefully
- more deployment and observability surfaces to manage
- more discipline required to avoid logic leaking across the boundary

## Reevaluation Triggers

Reevaluate this ADR if:

- the watch/control split becomes artificially expensive for simple flows
- operational overhead outweighs the separation benefits
- a more granular or more consolidated service model becomes clearly justified by evidence
