# Axon-Watch Delivery Plan

## Purpose

This document defines how work should be delivered in reviewable slices once
implementation of `/home/edp/axon-nvme/repos/axon-watch` begins.

It complements `IMPLEMENTATION_ROADMAP.md` by focusing on delivery shape rather
than only technical order.

## Delivery Rule

Ship thin, reviewable slices that each prove one meaningful outcome.

Avoid:

- giant foundational dumps
- broad UI rewrites without real flows
- backend sprawl before contracts are exercised

## Slice Principles

1. One slice should prove one visible or verifiable result.
2. Prefer end-to-end proof over isolated abstraction work.
3. Preserve repo clarity at every step.
4. Keep contracts ahead of integrations.
5. Keep the dedicated-server target visible even during local-first work.

## Suggested Delivery Sequence

### Slice 1 — Repo And Docs Foundation

Outcome:

- new repo exists
- canonical docs are migrated
- base folder structure is in place

Review focus:

- structure
- source-of-truth placement
- toolchain choices

### Slice 2 — Health And Shell

Outcome:

- `console-web`, `control-plane`, and `axon-watch` all start
- health endpoints exist
- shell renders with empty layout regions

Review focus:

- boundaries
- startup clarity
- no accidental complexity

### Slice 3 — Shared Contracts

Outcome:

- shared DTO/types package exists
- frontend and backend compile against the same run/signal/runtime vocabulary

Review focus:

- naming
- contract stability
- future-proofing

### Slice 4 — Runtime Strip + Summary

Outcome:

- the UI shows a real runtime summary from the control plane
- watch connectivity and degraded state are visible

Review focus:

- boot-critical DTO size
- truth ownership
- UI usefulness

### Slice 5 — Watch Signal Thin Slice

Outcome:

- one real signal is produced by `axon-watch`
- the control plane exposes it
- the UI renders it

Review focus:

- event envelope
- ranking behavior
- DTO cleanliness

### Slice 6 — Run-State Thin Slice

Outcome:

- one run progresses through canonical phases with real persisted state

Review focus:

- phase transitions
- stop/resume semantics
- history receipts

### Slice 7 — IDE Surface Thin Slice

Outcome:

- editor, terminal, and dock render with real shared state

Review focus:

- layout integrity
- state ownership
- no duplicate semantics

### Slice 8 — Approval And Review

Outcome:

- approval-required and review-ready flows are visible end to end

Review focus:

- guarded execution trust
- consistency across surfaces

### Slice 9 — Watch Depth

Outcome:

- richer signals, correlation, and delivery receipts

Review focus:

- signal model strength
- operator usefulness

### Slice 10 — Dedicated Server Readiness

Outcome:

- the stack is packaged for the target deployment model

Review focus:

- supervision
- reverse proxy
- portability

## Review Artifacts

Each slice should ideally include:

- a concise change summary
- verification steps
- screenshots or visual proof for UI changes
- API examples or payload references for contract changes
- explicit known risks

## Acceptance Criteria

The delivery plan is being followed when:

- slices stay reviewable
- proof arrives continuously
- architecture stays coherent while the product grows
