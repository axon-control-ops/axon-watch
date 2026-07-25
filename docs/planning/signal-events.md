# Axon-Watch Signal Events Contract

## Purpose

This document defines the canonical signal and inbox event model for the new
`axon-watch` product.

It is the source of truth for:

- signal event envelopes
- severity model
- signal ranking and inbox rules
- watch-to-control-plane event flow
- delivery receipts

## Core Rule

`axon-watch` is the upstream producer of monitoring and signal events.

The control plane may:

- read
- aggregate
- rank
- annotate
- dispatch actions

But it must not invent shadow signal types that bypass the canonical event model.

## Event Envelope

Every signal event should contain:

- `event_id`
- `signal_id`
- `event_type`
- `source`
- `workspace_id`
- `project_id`
- `severity`
- `status`
- `title`
- `body`
- `summary`
- `created_at`
- `updated_at`
- `occurred_at`
- `dedupe_key`
- `action_type`
- `action_payload`
- `correlation_ref`
- `delivery_state`
- `watch_rule`
- `meta`

## Signal Identity

### `signal_id`

Stable identity for the ongoing issue or monitored condition.

Example:

- one CI failure thread
- one stuck runtime
- one degraded connector

### `event_id`

Unique identity for a specific emitted event in that signal's history.

Example:

- signal opened
- severity escalated
- signal resolved
- delivery failed

## Event Types

Initial canonical event types:

- `signal_opened`
- `signal_updated`
- `signal_escalated`
- `signal_deescalated`
- `signal_resolved`
- `signal_reopened`
- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`
- `operator_acknowledged`
- `operator_dispatched`
- `operator_ignored`

## Watch Rule Model

Every signal event that can influence operator attention should include
`watch_rule`:

- `mode`: `observe` | `advise` | `approval` | `execute`
- `interrupts`: boolean
- `reason`: stable machine-readable reason code

This field is the canonical bridge between `KAIRO` operator presence and the
signal pipeline.

Source semantics to preserve from current Axon:

- approval-required items -> `approval`, interrupts
- execution-review items -> `execute`, interrupts when high urgency
- high urgency advisories -> `advise`, interrupts
- medium urgency advisories -> `advise`, non-interruptive
- low urgency ambient signals -> `observe`, non-interruptive

See [`KAIRO_MODE.md`](KAIRO_MODE.md).

## Severity Model

Canonical severities:

- `info`
- `warning`
- `high`
- `critical`

Severity meaning:

### `info`

Useful to know, but does not require intervention.

### `warning`

Needs attention soon, but not immediately blocking.

### `high`

Strong operator attention recommended. Can drive inbox prominence and delivery.

### `critical`

Immediate operator attention likely required. Eligible for interruptive delivery
according to policy.

## Signal Status

Canonical statuses:

- `open`
- `watching`
- `acknowledged`
- `suppressed`
- `resolved`
- `failed_delivery`

## Source Types

Suggested initial source values:

- `runtime`
- `watch`
- `ci`
- `git`
- `connector`
- `email`
- `workspace`
- `browser`
- `terminal`
- `approval`
- `deployment`
- `manual`

## Action Type

Signals may suggest or carry one primary action type:

- `open_dashboard`
- `open_workspace`
- `open_approvals`
- `review_changes`
- `retry`
- `investigate`
- `dispatch`
- `resolve`
- `none`

## Ranking / Inbox Rules

The inbox should rank signals using a stable rule set based on:

1. severity
2. recency
3. unresolved duration
4. operator-actionability
5. workspace priority

Important rule:

- inbox ranking must not mutate the underlying signal schema

## Correlation Rules

Signals may be correlated across sources.

Examples:

- CI failure + recent commit
- runtime degradation + high CPU warning
- connector issue + delivery failure

Correlation must be expressed through:

- `correlation_ref`
- related signal references in `meta`

## Dedupe Rules

Signals that represent the same underlying issue should share a stable
`dedupe_key`.

This prevents:

- duplicate inbox spam
- duplicate push notifications
- multiple unresolved rows for one underlying incident

## Delivery State

Delivery state captures the user-facing notification posture:

- `pending`
- `attempted`
- `delivered`
- `failed`
- `suppressed`
- `not_required`

## Delivery Receipts

Each delivery attempt should create a receipt containing:

- `receipt_id`
- `signal_id`
- `event_id`
- `channel`
- `attempted_at`
- `result`
- `error`
- `policy_reason`

Supported initial channels:

- `chat`
- `desktop`
- `mobile_push`
- `webhook`
- `slack`

## Watch-To-Control Plane Contract

`axon-watch` should publish structured signal records that the control plane can:

- fetch as snapshots
- stream as events
- translate into UI cards and inbox rows

The control plane should not have to parse raw watcher logs.

## UI Presentation Rules

Every signal shown in the UI should be renderable from canonical fields:

- title
- summary
- severity
- status
- source
- updated time
- suggested action

If a UI surface needs more information, it should request a new canonical field,
not invent an ad hoc representation.

## Resolution Rules

A signal is resolved only when:

- the underlying condition is cleared
- the signal record is updated to `resolved`
- the resolution becomes visible in history

Dismissal or hiding in the UI is not the same as resolution.

## Acceptance Criteria

This contract is being followed when:

- every signal in the product can be traced to a canonical event envelope
- all delivery attempts produce receipts
- the inbox is ranked without mutating raw signal truth
- different surfaces show the same severity and status for the same signal
