# Inbox `created_at` Schema Amendment

## Status

Approved and landed.

## Change

`SignalView` / `InboxItem` now includes `created_at` alongside `updated_at`.

This enables unresolved-duration inbox ranking without widening the schema
beyond fields already present on canonical signal events.

## Owners

- shared contract: `packages/shared-types/src/signals.ts`
- watch producers: `services/axon-watch/app/signals/*`
- control-plane projection: `services/control-plane/app/inbox_projection.py`
- ranking: `services/axon-watch/app/signals/ranking.py`

## Rule

- watch producers must populate `created_at` on inbox items
- control-plane projection must preserve `created_at` when present
- if `created_at` is missing from legacy payloads, projection falls back to
  `updated_at`

## Verification

- `tests/test_shared_contract_fixtures.py`
- `tests/test_watch_ranking.py`
- `tests/test_signal_consistency.py`
