# Axon-Watch Repo Bootstrap Spec

## Purpose

This document defines the exact initial scaffold for the new repo:

- `/home/edp/axon-nvme/repos/axon-watch`

It should be used as the blueprint for the first implementation pass when repo
creation begins.

## Bootstrap Goals

1. Create a clean source-of-truth repo structure.
2. Reflect the agreed service boundaries from day one.
3. Avoid carrying over legacy layout or ownership confusion.
4. Make local development and later dedicated-server deployment both straightforward.

## Top-Level Structure

```text
axon-watch/
  PRODUCT.md
  ARCHITECTURE.md
  README.md
  .env.example
  package.json
  pnpm-workspace.yaml
  pyproject.toml
  apps/
    console-web/
  services/
    control-plane/
    axon-watch/
  packages/
    shared-types/
    ui-contracts/
    prompt-contracts/
  docs/
    ui/
    contracts/
    adr/
  scripts/
    dev/
    ops/
    verify/
  infra/
    systemd/
    docker/
    caddy/
  tests/
    integration/
    e2e/
```

## Root Files

### `README.md`

Initial responsibilities:

- explain the product at a high level
- point to `PRODUCT.md` and `ARCHITECTURE.md`
- describe how to run the repo locally once implemented

### `PRODUCT.md`

Copy or migrate from the planning bundle once repo creation starts.

### `ARCHITECTURE.md`

Copy or migrate from the planning bundle once repo creation starts.

### `.env.example`

Should include:

- control-plane port
- watch service port
- public base URL
- storage paths
- auth-related placeholders

## Frontend App

Path:

- `apps/console-web/`

Suggested initial structure:

```text
apps/console-web/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.ts
    App.vue
    app/
    router/
    stores/
    components/
    features/
    styles/
```

Suggested feature folders:

- `layout/`
- `editor/`
- `terminal/`
- `agent-dock/`
- `signals/`
- `runtime/`
- `workspaces/`
- `approvals/`

## Control-Plane Service

Path:

- `services/control-plane/`

Suggested initial structure:

```text
services/control-plane/
  pyproject.toml
  app/
    main.py
    api/
    domain/
    orchestration/
    persistence/
    adapters/
  tests/
```

Minimum phase-1 endpoints:

- `/api/health`
- `/api/readiness`
- `/api/runtime/summary`
- `/api/runs`
- `/api/workspaces`

## Watch Service

Path:

- `services/axon-watch/`

Suggested initial structure:

```text
services/axon-watch/
  pyproject.toml
  app/
    main.py
    api/
    workers/
    signals/
    delivery/
    persistence/
    adapters/
  tests/
```

Minimum phase-1 endpoints:

- `/internal/watch/health`
- `/internal/watch/readiness`
- `/internal/watch/summary`
- `/internal/watch/inbox`

## Shared Packages

### `packages/shared-types/`

Purpose:

- shared DTO types for frontend and service contracts

### `packages/ui-contracts/`

Purpose:

- shared presentation-facing contract definitions

### `packages/prompt-contracts/`

Purpose:

- structured prompts, tool schemas, and execution-shape contracts that should
  not be hidden ad hoc inside runtime code

## Docs Structure

The planning docs should migrate into:

```text
docs/
  ui/
  contracts/
  adr/
```

Initial migration targets:

- `UI_SPEC.md` -> `docs/ui/`
- run/signal/API contracts -> `docs/contracts/`
- ADR files -> `docs/adr/`

## Infra Structure

### `infra/systemd/`

For dedicated server service units later.

### `infra/docker/`

For container-based local/prod-like runs.

### `infra/caddy/`

For reverse proxy and TLS examples.

## Scripts Structure

### `scripts/dev/`

Local development helpers.

### `scripts/ops/`

Operational scripts for process lifecycle and packaging.

### `scripts/verify/`

Cheap reliable verification entrypoints.

## Phase-1 Boot Behavior

The first scaffold should support:

1. starting `console-web`
2. starting `control-plane`
3. starting `axon-watch`
4. checking all service health endpoints

Even if all business logic is still stubbed.

## Acceptance Criteria

The bootstrap spec is being followed when:

- the repo structure matches the documented ownership model
- there is a place for every core concern before feature work starts
- no one needs to invent ad hoc folders during the first implementation pass
