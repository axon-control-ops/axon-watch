# ADR-002: Control Plane Owns Persisted Run Truth And Backend-Only Briefing

## Status

Accepted

## Context

Axon-Watch needs long-running, pausable, approval-aware work that remains
trustworthy across restarts and across multiple UI surfaces.

Pure prompt-driven ReAct is useful as a reasoning technique, but it is not a
sufficient source of truth for run phases, stop and resume behavior, approval
boundaries, review-ready state, or resumability.

The control-plane thin slice already persists runs in SQLite through
`services/control-plane/app/persistence/run_store.py`, exposes canonical
`/api/runs` routes with explicit transition rules, and assembles runtime summary
from that persisted state.

The product also needs a KAIRO-facing operator briefing projection. That API is
implemented at `GET /api/briefing` in `services/control-plane/app/operator_briefing.py`
with shared DTOs and contract tests, but the console shell does not consume it yet
during the current stabilization pass.

## Decision

The control plane owns persisted run truth for the product:

- explicit persisted run records with canonical phases and transition rules
- `/api/runs` as the authoritative run-state API
- runtime summary and inbox projections derived from control-plane state, not from
  prompt text or shell-local guesses

The shell consumes run truth through `/api/runs` and `/api/runtime/summary`. It
must not infer execution state from transcript text alone.

For the current stabilization pass, operator briefing remains backend-only:

- `GET /api/briefing` is implemented, verified, and contract-tested in the
  control plane
- the console shell does not wire briefing into live boot or dock behavior yet
- briefing must gate inbox-derived signals consistently with runtime summary when
  watch connectivity is degraded

Wire briefing into the shell only after the approval boundary and operator-action
projection strategy are explicitly locked, as documented in
`docs/contracts/BRIEFING-SEAM.md`.

## Alternatives Considered

### Use pure prompt-driven ReAct as the primary execution source of truth

Rejected because it does not provide sufficiently explicit, durable, cross-surface
state for stop, resume, approval, and review behavior.

### Use only ad hoc job rows without a canonical phase model

Rejected because the product needs explicit shared semantics, not only generic
task records.

### Wire `/api/briefing` into the shell immediately alongside run and approval seams

Rejected for the stabilization pass because it would introduce a second
operator-action projection surface before the approval boundary was locked and
would increase drift risk between briefing, runtime summary, and run controls.

## Trade-Offs

- Gains trust and consistency across run surfaces
- Costs more up-front modeling and persistence discipline
- Improves resumability and later durable orchestration options
- Keeps briefing verification moving without forcing premature shell coupling
- Defers KAIRO briefing card behavior until one projection strategy is chosen

## Consequences

### Positive

- consistent run-state across control-plane APIs, runtime summary, and shell run controls
- reliable stop, resume, approval, and review-ready semantics backed by SQLite persistence
- briefing contract and tests can evolve independently of shell boot dependencies
- runtime summary and briefing share the same watch-connectivity gate for inbox signals

### Negative

- requires more up-front modeling than prompt-only flows
- more DTO and persistence design work in the control plane
- operator briefing is not yet visible in the live shell
- stricter discipline around transitions, receipts, and projection ownership

## Reevaluation Triggers

Reevaluate this ADR if:

- the explicit phase model proves too rigid for real operator workflows
- shell wiring of briefing becomes safe because approval boundaries and projection
  strategy are locked
- a durable orchestration platform becomes necessary and materially changes the
  state model
- the transition cost of the current model outweighs its trust benefits
