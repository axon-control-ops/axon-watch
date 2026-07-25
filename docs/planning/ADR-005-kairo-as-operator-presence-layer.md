# ADR-005: KAIRO As Operator Presence Layer

## Status

Accepted

## Context

Current Axon implements the source capability under the **JARVIS** name across
many surfaces:

- persona prompts
- voice and spoken alerts
- voice command deck UI
- proactive watch rules
- delivery routing
- mobile operator cockpit behavior

The frozen AXON-X plan defined Watch, control plane, UI, and contracts well,
but did not yet define how this cross-cutting operator-presence concept should
be owned in the new repo.

Without an explicit decision, this capability risks becoming either:

- a discarded cosmetic feature, or
- a new monolith spread across frontend, backend, and watch code

For AXON-X, the renamed operator-presence layer is **KAIRO**:
**Knowledge-Augmented Intelligence for Response and Oversight**.

## Decision

Treat **KAIRO** as an operator-presence composition, not a single runtime mode.

Split ownership as follows:

- **`axon-watch`**: continuous watch, signal production, interruption inputs,
  delivery routing, receipts
- **`control-plane`**: advise/decide/execute workflow, approvals, briefing
  projection, voice/chat orchestration entrypoints
- **`console-web`**: operator cockpit, voice deck, spoken-alert presentation,
  ambient presence UI
- **`packages/prompt-contracts`**: persona and spoken-alert phrasing contracts

The old JARVIS toggle becomes a **KAIRO preset over explicit
operator-presence settings**, not a hidden global switch.

## Alternatives Considered

### Keep KAIRO as one frontend toggle with backend side effects

Rejected because it hides policy boundaries and makes Watch/control-plane
ownership unclear.

### Make KAIRO only a prompt/persona feature

Rejected because the value depends on watch, interruption, delivery, and voice
presence, not tone alone.

### Delay KAIRO entirely until after core IDE shell is complete

Rejected because watch/interruption/delivery are core to the product thesis and
should influence early contracts, even if full voice deck UI lands later.

## Trade-Offs

- Gains architectural clarity and cleaner migration seams
- Preserves the product's operator-foundation identity
- Requires explicit DTO fields for watch rules, delivery, and briefing
- Adds upfront design work before the voice UI slices

## Consequences

### Positive

- KAIRO aligns naturally with Axon-Watch as the always-on layer
- persona and presentation can evolve without corrupting run/signal truth
- migration from current Axon can be incremental and testable

### Negative

- more settings and contracts to define up front
- voice/mobile parity cannot be claimed until later slices land
- some current Axon JARVIS UI must be rewritten rather than copied

## Reevaluation Triggers

Reevaluate this ADR if:

- operator-presence settings become too fragmented for users to understand
- Watch and control-plane boundaries prove too rigid for voice/companion flows
- a simpler single-service model demonstrably reduces complexity without losing
  always-on behavior
