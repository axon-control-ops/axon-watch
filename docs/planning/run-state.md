# Axon-Watch Run State Contract

## Purpose

This document defines the canonical run-state model for the new `axon-watch`
product.

It is the source of truth for:

- active run lifecycle phases
- stop / resume / approval semantics
- operator-visible run summaries
- backend and frontend run-state contracts

The system must not rely on prompt text alone to infer execution state.

## Core Rule

There is one authoritative run-state model for the whole product.

The same state model must drive:

- control-plane APIs
- agent dock status
- operator dashboard status
- stop / resume controls
- approvals
- handoffs
- run history

## Entity Model

A run is a persisted execution record with:

- `run_id`
- `workspace_id`
- `lane_id`
- `mode`
- `status`
- `phase`
- `summary`
- `detail`
- `started_at`
- `updated_at`
- `ended_at`
- `can_stop`
- `can_resume`
- `can_approve`
- `can_review`
- `current_step`
- `history_ref`

## Mode

Mode identifies the execution style:

- `ask`
- `agent`
- `plan`
- `auto`
- `watch`

Mode is not the same thing as phase.

## Lifecycle Phases

The canonical phases are:

1. `queued`
2. `starting`
3. `planning`
4. `awaiting_input`
5. `awaiting_approval`
6. `executing`
7. `waiting_external`
8. `paused`
9. `review_ready`
10. `completed`
11. `failed`
12. `cancelled`

## Phase Meanings

### `queued`

The run exists but has not started executing yet.

### `starting`

The run has been accepted and is preparing resources, context, or workers.

### `planning`

The run is actively producing or refining a plan before tool execution.

### `awaiting_input`

The run cannot continue until the operator provides missing input or resolves a
question.

### `awaiting_approval`

The run is blocked on an explicit approval boundary before a guarded action.

### `executing`

The run is actively making progress through work steps or tool calls.

### `waiting_external`

The run is waiting on an external system, async job, background worker, or
durable orchestration callback.

### `paused`

The run was intentionally paused and is resumable.

### `review_ready`

The run has completed its active work and is waiting for review, apply/discard,
or follow-up action.

### `completed`

The run finished successfully.

### `failed`

The run reached a terminal error state.

### `cancelled`

The run was intentionally stopped and will not continue.

## Transition Rules

Allowed common transitions:

- `queued -> starting`
- `starting -> planning`
- `starting -> executing`
- `planning -> awaiting_input`
- `planning -> awaiting_approval`
- `planning -> executing`
- `executing -> waiting_external`
- `executing -> awaiting_approval`
- `executing -> review_ready`
- `executing -> completed`
- `executing -> failed`
- `executing -> paused`
- `waiting_external -> executing`
- `waiting_external -> paused`
- `queued -> paused`
- `starting -> paused`
- `planning -> paused`
- `awaiting_input -> planning`
- `awaiting_input -> cancelled`
- `awaiting_approval -> executing`
- `awaiting_approval -> cancelled`
- `paused -> executing`
- `paused -> cancelled`
- `review_ready -> completed`
- `review_ready -> executing`

Disallowed rule:

- the UI must not invent a phase that the backend did not persist

## Status vs Phase

`status` is a compact operator-facing category.

Suggested status categories:

- `running`
- `waiting`
- `blocked`
- `review`
- `done`
- `error`
- `stopped`

Mapping examples:

- `queued`, `starting`, `planning`, `executing` -> `running`
- `awaiting_input`, `waiting_external`, `paused` -> `waiting`
- `awaiting_approval` -> `blocked`
- `review_ready` -> `review`
- `completed` -> `done`
- `failed` -> `error`
- `cancelled` -> `stopped`

## Stop / Resume Rules

### Stop

`can_stop` is true when a run is in:

- `queued`
- `starting`
- `planning`
- `executing`
- `waiting_external`
- `awaiting_input`
- `awaiting_approval`
- `paused`

Stopping a run must produce a persisted state transition and a visible receipt.

### Resume

`can_resume` is true when a run is in:

- `paused`
- `awaiting_input`
- `review_ready` when a new bounded follow-up action is created

`awaiting_approval` is not resumable through the generic resume path. Forward
motion from the approval boundary requires an explicit approve or reject action.

Resume must not silently change mode from `plan` to `agent` or from guarded to
unguarded execution.

## Approval Rules

Approval state must be explicit, not inferred from tool logs.

When a run needs approval:

- phase becomes `awaiting_approval`
- `can_approve` becomes true
- the required action is described in structured fields
- the operator sees the same approval state in all surfaces

## Review Rules

Review-ready state must be explicit.

A run enters `review_ready` when:

- changes or results exist
- active execution has stopped
- a human decision is expected next

Examples:

- review generated changes
- approve apply/discard
- inspect receipts
- accept summary and close

## Source Of Truth Rule

The backend persisted run record is authoritative.

The frontend may keep transient UI hints such as:

- optimistic loading state
- panel open/closed state
- local animation state

But it must not override the canonical run phase.

## Presentation Contract

Each run should provide:

- short title
- short detail
- current step
- current phase
- operator-safe action labels

This prevents each surface from inventing its own explanation of what the run is
doing.

## History

Each run must keep a resumable execution history with:

- transitions
- timestamps
- actor or system source
- key action receipts
- error summaries
- approval decisions

## Acceptance Criteria

This contract is being followed when:

- every visible run can be mapped to a canonical phase
- stop/resume/approval behavior is consistent across surfaces
- the UI never guesses run truth from prompt text alone
- long-running or resumable work survives process restarts through persisted
  state
