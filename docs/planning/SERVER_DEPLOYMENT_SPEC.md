# Axon-Watch Server Deployment Spec

## Purpose

This document defines the target dedicated-server deployment shape for the new
`axon-watch` product.

It exists so the local-first build does not drift away from the long-term
operational target.

## Deployment Goal

The product must be able to move onto a dedicated server machine with minimal
architectural change.

The target deployment includes:

- one public web entrypoint
- one `control-plane` service
- one `axon-watch` service
- persistent local storage
- reverse proxy / TLS termination

## Target Topology

```text
internet
  -> tls proxy / reverse proxy
    -> console-web static assets
    -> control-plane api
    -> watch internal api
    -> persistent storage
```

## Service Processes

Required supervised processes:

1. `console-web` serving static or built assets
2. `control-plane`
3. `axon-watch`

Optional later processes:

- background workers
- durable workflow workers
- notification-specific workers

## Supervision Options

Preferred operational options to support:

- `systemd`
- Docker Compose

Optional later:

- Kubernetes or other orchestrators if scale demands it

## Reverse Proxy

The public entrypoint should sit behind a reverse proxy / TLS terminator.

Suggested options:

- Caddy
- Traefik
- Nginx

The application services should not be responsible for raw public TLS handling.

## Networking Rules

1. Public clients talk only to the public entrypoint.
2. `control-plane` and `axon-watch` may communicate over private local addresses.
3. Internal watch APIs should not be exposed publicly by default.
4. Public base URLs must be config-driven.

## Storage Rules

Phase-1 local-first storage may use SQLite on the same host.

Storage must be configured via explicit paths so the dedicated machine can own:

- run-state persistence
- signal persistence
- delivery receipts
- summary caches

## Secrets And Config

All environment-specific values should be externalized:

- ports
- service URLs
- storage paths
- auth settings
- notification credentials

Do not hard-code deployment addresses into UI or service logic.

## Health Model

The deployment must support:

- liveness for each service
- readiness for each service
- aggregate operator-facing degraded state

Suggested checks:

- `control-plane /api/health`
- `control-plane /api/readiness`
- `axon-watch /internal/watch/health`
- `axon-watch /internal/watch/readiness`

## Startup Order

Suggested startup order:

1. storage path availability
2. `axon-watch`
3. `control-plane`
4. static frontend serving
5. reverse proxy

Reason:

- watch should be available before the control plane tries to aggregate its state
- the control plane should expose summary APIs before the UI is made public

## Resilience Rules

The deployment should tolerate:

- watch restart without data-loss of summaries or signal history
- control-plane restart without loss of monitoring continuity
- proxy restart without logical state loss

## Acceptance Criteria

This spec is being honored when:

- the system can be run locally in a shape close to the server topology
- the same service boundaries survive migration to a dedicated machine
- no redesign is needed to separate public traffic from internal watch APIs
