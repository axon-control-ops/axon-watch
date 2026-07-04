# Axon-X Architecture Spec

## Topology

The new product lives in a new repo:

- `/home/edp/axon-nvme/repos/axon-watch`

It should contain three primary implementation surfaces:

1. `console-web`
2. `control-plane`
3. `axon-watch`

## Service Ownership

### `console-web`

Frontend application responsible for:

- layout shell
- workspace navigation
- editor and terminal surfaces
- agent dock
- signals and approvals UI
- runtime and monitoring presentation

### `control-plane`

Interactive backend responsible for:

- auth and sessions
- chat and agent APIs
- approvals
- execution dispatch
- workspace handoffs
- UI-facing aggregation
- run-state truth

### `axon-watch`

Dedicated watcher service responsible for:

- monitoring loops
- runtime and connector observation
- signal normalization
- signal correlation
- notification routing
- delivery receipts
- durable monitoring summaries

## Boundary Rule

The architectural contract is:

```text
Watch detects and persists.
Control plane decides and acts.
UI presents and steers.
```

No service should silently absorb the responsibilities of another service.

## Deployment Modes

### Mode 1: Local Development

Run all services on one machine:

- frontend dev server
- control-plane API
- watch service
- local storage

### Mode 2: Local Production-Like

Run the same services under a supervisor with a reverse proxy and production-like
configuration.

### Mode 3: Dedicated Server

Move the same services onto a dedicated machine with minimal topology changes.

This is the default long-term portability target.

## Dedicated Server Portability Rules

To keep migration low-hassle later:

1. Services must communicate through explicit APIs, not hidden shared memory.
2. Config, secrets, and storage paths must be externalized.
3. Public access must go through a reverse proxy / TLS terminator.
4. Each service must expose health/readiness endpoints.
5. Startup order must be documented and reproducible.
6. No frontend contract should assume `localhost` directly.
7. Service discovery must be config-driven.

## Persistence Strategy

Initial local-first persistence can use SQLite in WAL mode on the same host for:

- signal events
- inbox items
- delivery receipts
- runtime summaries
- resumable execution metadata

Important rule:

- design storage adapters so persistence can evolve later if cross-host separation
  becomes necessary

## Execution Backbone

Pure prompt-driven ReAct should not be the system backbone.

The backbone should be:

1. explicit run-state machine or workflow history
2. structured tool/function calls
3. persisted execution records
4. optional reasoning/planning inside bounded execution steps

## Orchestration Direction

Short term:

- explicit persisted run records
- structured tool calling
- resumable jobs

Longer term:

- leave room for durable workflow orchestration such as Temporal if long-running,
  pausable, failure-prone flows become central enough to justify it

## Watch Transport

Preferred initial transport between `control-plane` and `axon-watch`:

- loopback HTTP or Unix socket

The interface must stay stable enough that later deployment onto a dedicated
machine is still easy.

## Streaming Strategy

For watcher-originated UI updates:

- prefer SSE for one-way status and event streams
- use WebSockets only when true bidirectional live control is required

## Repo Structure Direction

Suggested shape:

```text
axon-watch/
  apps/console-web/
  services/control-plane/
  services/axon-watch/
  docs/
  packages/
  scripts/
  infra/
```

## Import Policy

All imports from the current `axon-local` repo must be classified as:

- `adopt`
- `adapt`
- `rewrite`
- `discard`

Nothing should be copied in without a clear new owner in the new architecture.

## Acceptance Criteria

The architecture is acceptable when:

- the control plane can restart without killing monitoring continuity
- the UI still has one coherent runtime truth
- the system can be moved onto a dedicated machine without redesigning service boundaries
- copied features from Axon are reduced to bounded, owned modules instead of legacy sprawl
