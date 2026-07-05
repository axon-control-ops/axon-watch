# Axon-Watch API Contract

## Purpose

This document defines the initial local API contract between:

- `axon-watch`
- `control-plane`

It does not yet define public internet-facing endpoints. It defines the internal
service boundary that should work:

- on one local machine
- under local production-like supervision
- on a dedicated server later

## API Design Goals

1. Explicit service ownership
2. Low-friction local-first development
3. Easy dedicated-server portability
4. Stable DTOs for UI-facing aggregation
5. No hidden shared-memory dependency

## Transport

Preferred initial transport:

- loopback HTTP

Optional later transport:

- Unix socket

The DTO and endpoint contracts should remain stable even if transport changes.

## Base Path

Suggested internal base path:

- `/internal/watch`

## Required Endpoints

### `GET /internal/watch/health`

Purpose:

- basic liveness for the watcher process

Response shape:

- `status`
- `service`
- `version`
- `time`

### `GET /internal/watch/readiness`

Purpose:

- readiness for dependent use by the control plane

Response shape:

- `status`
- `dependencies`
- `storage`
- `worker_state`
- `issues`

### `GET /internal/watch/summary`

Purpose:

- lightweight aggregate snapshot for control-plane overview

Response shape:

- `status`
- `signals`
- `inbox`
- `connectors`
- `runtime`
- `updated_at`

### `GET /internal/watch/inbox`

Purpose:

- ranked current inbox items

Response shape:

- `items`
- `count`
- `updated_at`

### `GET /internal/watch/signals`

Purpose:

- paginated canonical signal list

Query support:

- `workspace_id`
- `severity`
- `status`
- `source`
- `limit`
- `cursor`

### `GET /internal/watch/signals/{signal_id}`

Purpose:

- full detail for one signal

Response shape:

- canonical signal record
- recent event history
- suggested action
- delivery state

### `GET /internal/watch/events`

Purpose:

- event stream or incremental pull surface for signal updates

Initial implementation options:

- SSE stream
- or polling endpoint with cursor-based pagination

### `POST /internal/watch/commands`

Purpose:

- control-plane sends a bounded command to the watcher

Examples:

- rescan
- reprobe connector
- re-evaluate signal
- acknowledge signal
- suppress signal

Request shape:

- `command_id`
- `command_type`
- `target_type`
- `target_id`
- `requested_by`
- `payload`
- `requested_at`

Response shape:

- `accepted`
- `command_id`
- `status`
- `receipt`

### `GET /internal/watch/commands/{command_id}`

Purpose:

- retrieve command execution status and receipt

## DTO Rules

All watch DTOs must be:

- explicit
- typed
- versionable
- stable across frontend surfaces

DTO changes must be:

- additive first where possible
- documented in canonical contracts
- reflected in frontend shared types

## Snapshot vs Event Rules

Use two access patterns:

### Snapshot

For:

- current dashboard state
- current inbox
- current runtime summary

### Event Stream

For:

- live updates
- signal transitions
- delivery receipts
- watcher health changes

Do not make the frontend reconstruct the full product state from raw event replay
alone.

## Auth Boundary

Initial local development may trust loopback-only transport behind the control
plane boundary.

Long-term rule:

- the watcher must still support authenticated service-to-service access when
  moved to a dedicated machine

## Reliability Rules

The watcher API must:

- expose health and readiness separately
- return stable failure payloads
- avoid blocking the control-plane boot on heavy probe work
- return cached summaries where appropriate

## Error Model

Every failure response should provide:

- `error_code`
- `message`
- `retryable`
- `details`

## Versioning Rule

Suggested initial version approach:

- internal DTO version field
- contract changes documented in markdown ADR/contracts before rollout

## Acceptance Criteria

This contract is being followed when:

- the control plane can function without direct watcher memory access
- the watcher can restart independently and recover its summaries
- the same API can work locally and on a dedicated server later
- frontend aggregation relies on stable snapshots and events instead of parsing
  logs or internal watcher state
