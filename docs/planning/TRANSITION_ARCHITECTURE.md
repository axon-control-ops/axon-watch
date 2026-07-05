# Axon-Watch Transition Architecture

## Purpose

This document defines the migration seam between:

- the existing `axon-local` system
- the new `axon-watch` system

It is the explicit transitional architecture that turns this plan into a
Strangler-style migration rather than only a greenfield target.

## Transition Goal

The migration should happen through visible, bounded seams with reversible
deliveries.

The new system must be able to coexist with the old system during transition
without unclear ownership of user-facing flows.

## Core Migration Rule

At any time, each capability must answer:

1. Which system owns it right now?
2. If both systems coexist, what is the façade or seam?
3. How do we roll back if the migrated capability regresses?

## What Stays In `axon-local`

Initially, `axon-local` continues to own:

- current production or active developer workflows
- current console UI
- current mission and operator flows
- existing packaging/runtime environment

It remains the live reference system until equivalent thin slices in
`axon-watch` are verified.

## What Routes First To `axon-watch`

The earliest migrated capabilities should be:

1. new repo structure and shell only
2. runtime summary thin slice
3. first watch-produced signal/inbox slice
4. first canonical run-state slice

These are chosen because they exercise the new boundaries without forcing an
all-at-once replacement.

## Transitional Façade / Proxy Strategy

During coexistence, use façade/proxy patterns deliberately where needed.

Examples:

- a façade in the new control plane that can normalize old-style data into new DTOs
- a compatibility projection from watch summaries into control-plane runtime strips
- optional old-to-new adapter endpoints if an interim integration is required

Rule:

- façades must translate and isolate differences
- façades must not become permanent dumping grounds

## UI Ownership Decision Rule

When both systems exist, the UI must know which backend owns which flow.

Decision principles:

- if a flow depends on canonical new run-state, the new `control-plane` owns it
- if a flow depends on watcher-produced canonical signal events, the new
  `axon-watch` owns the underlying truth
- if a flow has not yet migrated, `axon-local` remains the owner

No UI surface should silently merge conflicting truths from both systems without
a defined anti-corruption layer.

## Anti-Corruption Layer Rules

If old and new models differ, use an explicit anti-corruption layer.

The ACL must:

- map old identities into new DTOs explicitly
- preserve source identity metadata
- normalize severity, status, and run-state meanings
- reject ambiguous data rather than inventing fake precision

The ACL must not:

- leak old internal model quirks into new core domain models
- redefine canonical new semantics on the fly

## Capability Transition Table

| Capability | Initial owner | Migration seam | New owner | Rollback rule |
|---|---|---|---|---|
| Runtime summary | `axon-local` | New runtime summary DTO and façade-compatible aggregator | `control-plane` | Fallback to old runtime summary source while preserving shell startup |
| Signal / inbox | `axon-local` | Watch canonical event model plus control-plane projection | `axon-watch` + `control-plane` | Fall back to old signal source; keep new UI signal surfaces behind explicit switch if needed |
| Run-state | `axon-local` | Canonical run-state DTO and transition model | `control-plane` | Route run initiation back to old system until transition integrity is restored |
| Approval flow | `axon-local` | Explicit approval DTO and phase boundary | `control-plane` | Revert guarded actions to old approval path if safety semantics regress |
| Workspace handoffs | `axon-local` | Shared workspace and handoff record model | `control-plane` | Use old handoff workflow until cross-workspace state is trustworthy |
| IDE shell | none in final new form | New shell hosted separately from old UI | `console-web` | Keep old console as primary until new shell reaches verified parity |
| KAIRO watch rules + delivery | `axon-local` proactive watcher + notification policy | Canonical signal `watch_rule` + delivery receipts in Watch; briefing projection in control plane | `axon-watch` + `control-plane` + `console-web` | Fall back to old proactive/inbox source; disable new spoken-alert preset until receipts and briefing DTOs are trustworthy |
| KAIRO persona + voice presence | `axon-local` voice modules + companion runtime | Persona contracts + Vue operator-presence layer over new DTOs | `packages/prompt-contracts` + `console-web` | Keep old voice/deck paths active until new briefing/signal subscriptions are verified |
| Mobile operator cockpit | `axon-local` mobile JARVIS controller | Vue compact operator-presence surfaces | `console-web` | Keep old mobile cockpit until briefing/inbox parity is verified; do not claim background listening during transition |

## KAIRO Transition Rule

Do not treat `KAIRO` as a single cutover toggle.

Transition order:

1. Watch emits canonical signals with `watch_rule` metadata
2. Watch owns delivery attempts and receipts for watch-born events
3. Control plane exposes briefing/inbox projections from canonical state
4. Vue operator-presence layer consumes those DTOs for deck and spoken alerts
5. Persona contracts layer on top without changing run/signal truth

During coexistence, old Axon may continue to own live voice/companion paths while
new Watch and control-plane DTOs become authoritative for attention and
interruption policy.

## Rollback Rules

Every migrated capability must define:

- fallback owner
- fallback route or UI behavior
- state compatibility requirement
- verification needed before retrying migration

Rollback must be capability-scoped where possible, not system-wide.

## Delivery Discipline

Transition work should prefer:

- coexistence through small seams
- explicit capability ownership
- reversible thin slices

Avoid:

- hidden cutovers
- mixed truth without ACLs
- broad rewrites that skip transitional verification

## Acceptance Criteria

This architecture is being followed when:

- old and new systems can coexist without ambiguous ownership
- migrated capabilities have clear seams and rollback paths
- new canonical models stay clean even while old and new systems overlap
