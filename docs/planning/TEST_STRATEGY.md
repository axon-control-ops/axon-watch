# Axon-Watch Test Strategy

## Purpose

This document defines the testing strategy for the new
`/home/edp/axon-nvme/repos/axon-watch` repo.

The goal is to keep confidence high without rebuilding the current repo’s test
sprawl on day one.

## Testing Principles

1. Test contracts and boundaries first.
2. Prefer focused tests over noisy duplication.
3. Ensure at least one end-to-end proof exists for every major flow.
4. Keep UI verification grounded in visible behavior.
5. Test state transitions explicitly where trust matters.

## Test Layers

### 1. Unit Tests

Use for:

- DTO validation
- ranking logic
- phase transition logic
- correlation helpers
- small UI view-model helpers

Primary targets:

- run-state transition rules
- signal ranking rules
- runtime summary assembly
- approval gating helpers

### 2. Service Integration Tests

Use for:

- `control-plane` route behavior
- `axon-watch` route behavior
- control-plane to watch integration
- persistence adapters

Primary targets:

- health/readiness
- watch summary and inbox endpoints
- run creation and lifecycle mutation endpoints
- approval endpoints

### 3. Frontend Integration Tests

Use for:

- layout mode switching
- shared store behavior
- runtime strip rendering
- signal rendering
- dock state behavior

Primary targets:

- operator vs IDE layout consistency
- one run-state model across surfaces
- one signal model across surfaces

### 4. End-To-End Tests

Use for:

- one real shell boot
- one real signal flow
- one real run flow
- one approval flow

These should stay thin and high-value.

## Test Priorities By Phase

### Early Repo Bootstrap

Need:

- health endpoint checks
- shell render checks
- basic wiring tests

### Contract Phase

Need:

- DTO schema and shape checks
- transition rules
- summary assembly

### First Thin Slices

Need:

- one signal end-to-end test
- one run-state end-to-end test
- one approval test

### IDE Surface Phase

Need:

- layout integrity checks
- editor/dock/terminal shared-state checks

## UI Verification Strategy

For visible UI slices:

- capture screenshots or visual receipts
- verify both `operator` and `ide` modes when shared state is affected
- verify that the same run/signal truth is shown in multiple surfaces

Do not rely only on unit tests for high-visibility UI behavior.

## Trust-Critical Areas

These must receive explicit tests:

- stop/resume
- approval-required transitions
- review-ready transitions
- signal severity/ranking
- signal delivery receipts
- watcher reconnect/restart behavior

## Performance-Oriented Checks

The repo should also maintain a small set of practical checks for:

- runtime summary latency
- watch summary latency
- shell boot readiness
- cross-service startup readiness

These do not need to start as full benchmarks, but they should exist as cheap,
repeatable checks.

## Non-Goals

- rebuilding every historic test from `axon-local`
- using giant snapshot suites as the primary UI safety net
- forcing every module to have tests before any thin slice exists

## Acceptance Criteria

The test strategy is being followed when:

- every trust-critical contract has focused coverage
- each major product flow has at least one end-to-end proof
- test coverage grows with architecture, not ahead of it in a noisy way
