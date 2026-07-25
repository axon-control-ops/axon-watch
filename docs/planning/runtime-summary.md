# Axon-Watch Runtime Summary Contract

## Purpose

This document defines the shared runtime summary DTO used by the UI to learn:

- what runtime is active
- whether the system is healthy enough to operate
- what work is currently active
- what watcher-backed issues need immediate attention

It is the canonical DTO contract for boot-critical runtime identity and the most
important operator-facing summary surfaces.

## Design Goal

The runtime summary must be:

- fast to compute
- stable across layout modes
- sufficient for initial shell rendering
- explicit about what is active vs degraded vs unknown

## Core Rule

The runtime summary is a **summary DTO**, not a dumping ground for every detail.

Detailed data belongs in:

- run detail endpoints
- signal detail endpoints
- watcher summary endpoints
- chat/thread history endpoints

## Top-Level Shape

Suggested fields:

- `generated_at`
- `control_plane`
- `watch`
- `runtime_identity`
- `active_runs`
- `approvals`
- `signals`
- `capabilities`
- `degraded`

## `control_plane`

Describes the interactive backend.

Suggested fields:

- `status`
- `version`
- `uptime_seconds`
- `ready`

## `watch`

Describes the watcher service.

Suggested fields:

- `status`
- `connected`
- `last_summary_at`
- `degraded_reason`

## `runtime_identity`

Describes the current execution/runtime identity the UI should display.

Suggested fields:

- `provider_family`
- `provider_name`
- `model_name`
- `mode_default`
- `tool_calling_supported`
- `reasoning_supported`

## `active_runs`

Compact list of active run summaries.

Each row should include:

- `run_id`
- `workspace_id`
- `mode`
- `status`
- `phase`
- `title`
- `detail`
- `lane_id`
- `updated_at`

## `approvals`

Compact approval summary.

Suggested fields:

- `pending_count`
- `highest_severity`
- `latest_approval_at`

## `signals`

Compact watch-backed signal summary.

Suggested fields:

- `open_count`
- `critical_count`
- `high_count`
- `top_items`
- `last_updated_at`

`top_items` should remain lightweight and not replace the canonical inbox API.

## `capabilities`

Operator-visible capability summary.

Suggested fields:

- `editor`
- `terminal`
- `browser_preview`
- `watch_connected`
- `approvals_enabled`
- `notifications_enabled`

## `degraded`

Boolean plus optional structured reasons indicating whether the overall operator
surface is degraded.

Suggested fields:

- `active`
- `reasons`

## Boot Contract

The frontend may rely on this DTO to:

- decide what status strip to show
- render the first operator/runtime chips
- know whether watch is connected
- know whether active runs already exist

The frontend must not need to block on full signal history or full chat history
to render the initial shell.

## Presentation Rules

The same DTO should feed:

- topbar/runtime strip
- status bar truth strip
- right-dock run/signal/approval seam summaries
- startup status surfaces

Different UI surfaces may style it differently, but must not reinterpret its
core meaning.

Region-level binding details live in
[`UI_COMPOSITION_SPEC.md`](UI_COMPOSITION_SPEC.md).

## Performance Rule

The summary must be cached or assembled cheaply enough to support boot and
frequent refresh without re-running the heaviest probes inline.

## Acceptance Criteria

This contract is being followed when:

- the initial shell can render from a small explicit DTO
- watch connectivity is visible without opening deep diagnostics
- active-run and degradation summaries are consistent across surfaces
- the summary stays small, stable, and fast instead of becoming a catch-all payload
