# Axon-Watch Control-Plane API Contract

## Purpose

This document defines the initial control-plane API contract for the new
`axon-watch` product.

It is the canonical source of truth for UI-facing endpoints that power:

- chat and composer actions
- run-state reads and mutations
- approvals
- workspace handoffs
- runtime overview
- watch-backed signal aggregation

## Ownership Rule

The control plane owns:

- operator and user interaction APIs
- run-state truth
- approvals and guarded actions
- chat and agent orchestration entrypoints
- UI-facing aggregation of watch data

The control plane does **not** own:

- raw monitoring loops
- signal production
- connector polling
- direct watcher-only persistence

## Base Path

Suggested primary base path:

- `/api`

## Required Endpoint Groups

### Health

- `GET /api/health`
- `GET /api/readiness`

These represent the control-plane process itself, not the full product health by
default.

### Runtime Summary

- `GET /api/runtime/summary`

Purpose:

- return the control-plane runtime identity, active run overview, and merged
  watch-aware summary used during boot and steady-state UI rendering

### Operator Briefing

- `GET /api/briefing`

Purpose:

- return the KAIRO-facing operator briefing projection used by the right-dock
  briefing card, spoken-alert eligibility, and compact mobile/operator surfaces

Suggested fields:

- `generated_at`
- `headline`
- `notice`
- `advise`
- `next_safe_action`
- `pending_approvals_count`
- `active_runs_count`
- `top_signal`
- `degraded_summary`
- `presence_state`

Rules:

- briefing copy may be persona-aware
- counts, phases, severities, and action eligibility must come from canonical
  run/signal/approval state
- briefing failure must not block shell boot; UI falls back to `RuntimeSummary`

### Runs

- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs`
- `POST /api/runs/{run_id}/stop`
- `POST /api/runs/{run_id}/resume`
- `POST /api/runs/{run_id}/approve`
- `POST /api/runs/{run_id}/reject`

Purpose:

- create and control explicit persisted runs
- expose canonical run state to all UI surfaces

### Chat / Composer

- `POST /api/chat/messages`
- `GET /api/chat/threads/{thread_id}`
- `GET /api/chat/threads/{thread_id}/history`

Purpose:

- accept operator intent
- attach messages to threads and runs
- surface conversation history independently from run-state truth

### Workspaces

- `GET /api/workspaces`
- `GET /api/workspaces/{workspace_id}`
- `POST /api/workspaces/{workspace_id}/handoffs`

Purpose:

- workspace navigation
- workspace identity
- cross-workspace execution handoff

### Approvals

- `GET /api/approvals`
- `GET /api/approvals/{approval_id}`
- `POST /api/approvals/{approval_id}/approve`
- `POST /api/approvals/{approval_id}/reject`

Purpose:

- expose and resolve explicit guarded actions

### Signals / Inbox

- `GET /api/inbox`
- `GET /api/signals`
- `GET /api/signals/{signal_id}`

Purpose:

- return control-plane-facing ranked and annotated views built on watch-produced
  canonical signals

### Live Updates

- `GET /api/live/events`

Purpose:

- SSE-first live update surface for run-state, approvals, and watch-backed
  signal/inbox changes

## Contract Rules

1. The UI must not need separate hidden APIs for the same concept.
2. Run-state reads must come from canonical run records.
3. Approval state must be explicit and queryable.
4. Signal/inbox APIs may enrich watch data but must preserve canonical IDs and
   severities.
5. Boot-critical runtime summary must be lightweight and stable.

## DTO Rules

Primary DTO families:

- `RunRecord`
- `ApprovalRecord`
- `WorkspaceRecord`
- `RuntimeSummary`
- `InboxItem`
- `SignalView`
- `ThreadMessage`

All DTOs must be:

- typed
- versionable
- additive-first
- documented in canonical markdown contracts

## Boot Rule

The frontend should be able to boot its first useful shell from:

1. settings/config bootstrap
2. workspace list
3. runtime summary
4. optional live event stream

The UI must not require heavy signal history or full chat history before initial
render.

## Aggregation Rule

The control plane may enrich watch data with:

- operator-specific ranking
- workspace display metadata
- action affordances
- merged runtime context

But it must not silently fork the signal identity model.

## Acceptance Criteria

This contract is being followed when:

- the frontend can render all major surfaces from explicit DTOs
- run, approval, workspace, and signal state do not require scraping logs or prompt text
- the control plane can evolve independently from watcher internals as long as the documented contracts stay stable
