# Axon-Watch Fitness Functions

## Purpose

This document defines measurable architectural guardrails for the new
`axon-watch` product.

These are the enforceable or monitorable checks that turn architectural intent
into operational discipline.

## Rule

Every fitness function must declare:

- metric
- threshold
- how it is measured
- CI gate vs nightly gate
- owner

If a target is not yet practical as a CI gate, it should still be defined and
tracked as a nightly or periodic gate until it can be tightened.

## Fitness Functions

| Metric | Threshold | How it is measured | Gate type | Owner |
|---|---|---|---|---|
| Shell boot readiness budget | Initial usable shell in `<= 2500ms` on standard dev hardware after frontend app load, excluding cold install/setup | Browser automation measures first render of shell regions after boot-critical APIs complete | Nightly at first, later CI smoke | `console-web` |
| Runtime summary latency budget | `p95 <= 300ms` for `/api/runtime/summary` in local production-like mode | Targeted route timing test with warm service state | CI gate |
| Watch summary latency budget | `p95 <= 200ms` for `/internal/watch/summary` under normal load | Service integration timing test | CI gate |
| Run-state propagation latency | Run phase change visible in all subscribed UI surfaces within `<= 500ms` under local production-like mode | End-to-end test timestamps state mutation and UI observation | Nightly gate |
| Service readiness budget | Each service reaches readiness within `<= 10s` from process start in local production-like mode | Startup harness records process start and readiness endpoint success | CI smoke |
| Allowed dependency directions | No dependency from `axon-watch` into UI code; no frontend direct dependency on watcher internals; no circular dependency between `control-plane` and `axon-watch` domain layers | Static import boundary checks and repo structure lint | CI gate |
| Maximum boot-critical DTO size | Runtime summary payload `<= 32 KB` JSON body in normal conditions | Contract test serializes representative payload and checks byte size | CI gate |
| Maximum watch summary payload size | Watch summary payload `<= 24 KB` JSON body in normal conditions | Contract test serializes representative payload and checks byte size | CI gate |
| Signal inbox consistency | Same `signal_id`, severity, and status visible across summary, inbox, and detail projections | Contract/integration test comparing projected representations | CI gate |
| Approval transition integrity | Approval-required runs must enter `awaiting_approval` before guarded execution continues | Run-state transition test and end-to-end approval flow | CI gate |
| Stop/resume integrity | A stopped or paused run must produce explicit persisted transitions and receipts | Integration test on run mutation endpoints | CI gate |
| Watch restart continuity | Watch service restart must preserve signal history and recover summaries without control-plane schema drift | Restart harness in local production-like mode | Nightly gate |
| KAIRO watch-rule consistency | Same signal payload must map to the same `watch_rule.mode` across ranking, delivery, and briefing projections | Contract test on representative signal fixtures | CI gate |
| Spoken-alert eligibility latency | High-severity interruptive signal becomes eligible for spoken alert within `<= 1000ms` after control-plane projection in local mode | End-to-end test from signal event to voice-eligibility DTO | Nightly gate |
| Delivery receipt completeness | Critical interruptive signals must produce at least one delivery receipt or explicit `delivery_failed` event | Contract/integration test on delivery lifecycle | CI gate |
| Briefing API latency budget | `p95 <= 400ms` for operator briefing endpoint under normal load | Route timing test with seeded signals/runs/approvals | CI gate |
| Privacy-mode gating correctness | Spoken alerts and interruptive delivery must be suppressed when privacy mode blocks them | Policy test matrix on presence + privacy settings | CI gate |

## Measurement Notes

### Standard Environment

Performance-oriented thresholds should be measured in a documented reference
environment, for example:

- local production-like run
- single developer machine profile
- seeded representative data volume

These numbers should be revisited once the new repo has a stable baseline.

### CI vs Nightly

Use CI gates for:

- fast deterministic checks
- DTO size checks
- dependency direction checks
- route-level latency where stable enough

Use nightly gates for:

- full browser timing
- restart continuity
- propagation latency under a more complete stack

## Failure Policy

When a fitness function fails:

- CI gate failures block merge for CI-classified checks
- nightly failures create an actionable issue with owner and regression details

## Evolution Rule

Thresholds may be tightened over time, but not loosened silently.

Any threshold change must document:

- reason for change
- prior threshold
- new threshold
- evidence supporting the change

## Acceptance Criteria

This spec is being followed when:

- architectural quality is measured, not only described
- regressions are surfaced early
- performance and boundary intent become part of delivery discipline
