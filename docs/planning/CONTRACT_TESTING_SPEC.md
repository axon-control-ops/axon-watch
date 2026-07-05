# Axon-Watch Contract Testing Spec

## Purpose

This document defines executable contract verification between:

- `control-plane`
- `axon-watch`

Documentation is necessary, but not sufficient. Service compatibility must be
testable and gated.

## Contract Testing Goal

The new system should evolve service boundaries safely through:

- shared schemas/types source of truth
- executable provider/consumer verification
- additive-first change rules
- compatibility gates in CI

## Shared Schema Rule

There must be one canonical schema/type source of truth for cross-service DTOs.

Primary candidates:

- shared typed package(s) in the new repo
- generated or manually curated schema artifacts derived from those types

The same contract source should drive:

- service DTO validation
- frontend shared types
- contract verification fixtures

## Contract Families

Initial contract families:

- `RunRecord`
- `RuntimeSummary`
- `SignalEvent`
- `InboxItem`
- `WatchSummary`
- `ApprovalRecord`
- command request/receipt DTOs

## Consumer / Provider Verification Flow

### Provider Side

The provider service verifies that:

- its responses conform to the canonical schema
- required fields remain present
- enum values and status mappings stay valid

### Consumer Side

The consumer verifies that:

- it can parse and use provider fixtures and current provider output
- optional/additive fields do not break consumption

## Verification Pattern

Recommended approach:

1. canonical schema/type definitions live in shared package(s)
2. provider tests validate emitted payloads against those definitions
3. consumer tests validate parsing/rendering using canonical fixtures
4. CI runs compatibility checks before merge

## Versioning Rules

1. DTO evolution is additive-first whenever possible.
2. Breaking changes require:
   - a new version marker or explicit migration path
   - updated consumer tests
   - documented rollout steps
3. Silent breaking changes are not allowed.

## Additive-First Evolution Rules

Allowed without breaking compatibility:

- adding optional fields
- adding new enum values only when consumers are prepared to tolerate unknowns
- adding new endpoints

Potentially breaking:

- removing fields
- changing field meaning
- changing type/nullability
- narrowing enums without migration

## Deprecation / Removal Process

To remove or change a contract field:

1. mark it deprecated in contract docs
2. add or document the replacement field
3. update provider tests
4. update consumer tests
5. keep compatibility through a defined grace period
6. remove only after the new path is verified and the grace period ends

## CI Compatibility Gate

The CI gate should fail when:

- provider payloads violate canonical schema
- consumer fixtures no longer parse correctly
- dependency direction rules are broken for shared contract packages
- undocumented breaking DTO changes are introduced

## Nightly / Extended Verification

Nightly or extended gates may also verify:

- cross-service end-to-end event flow
- restart continuity with preserved payload compatibility
- browser rendering against live provider payloads

## Ownership

Contract ownership should be explicit:

- shared contract package maintainers own schema truth
- service owners own provider correctness
- consuming app owners own consumer tolerance and rendering correctness

## Acceptance Criteria

This spec is being followed when:

- service compatibility is enforced by tests, not only by documentation
- additive evolution is normal and safe
- breaking changes require visible migration intent
- CI catches incompatible service contract drift before merge
