# Delivery Receipts for Operator Attention

## Purpose

Critical and high-severity watch-born signals must produce **delivery receipts**
so operator attention is traceable — not just ranked in the inbox.

This slice implements the bootstrap delivery policy in `axon-watch` with
control-plane projection and Attention sidebar visibility.

## Ownership

| Surface | Responsibility |
|---|---|
| `axon-watch/app/delivery/` | Channel policy, receipt store, delivery attempts |
| `axon-watch/app/signals/store.py` | Enriches inbox items with `delivery_state` |
| `control-plane` | `/api/delivery/receipts` proxy + inbox projection |
| `console-web` | Attention sidebar delivery badge on top signals |

## Receipt shape

Each receipt contains:

- `receipt_id`
- `signal_id`
- `event_id`
- `channel`
- `attempted_at`
- `result` — `succeeded` | `failed` | `muted`
- `error`
- `policy_reason`

Fixture: `packages/shared-types/fixtures/delivery-receipt.example.json`

## Bootstrap policy (v1)

Severity routing (channels attempted once per signal):

| Severity | Channels |
|---|---|
| `info` | `inbox` (skipped when `delivery_state: not_required`) |
| `warning` | `inbox` |
| `high` | `inbox`, `desktop` |
| `critical` | `inbox`, `desktop` |

v1 simulates successful `inbox` and `desktop` delivery in-process. External
push/Slack/webhook channels are recorded as failed with `channel_unavailable`.

Dedupe: successful `signal_id + channel` pairs are not re-delivered on repeated
inbox reads.

## Routes

Watch (internal):

- `GET /internal/watch/delivery/receipts?limit=&cursor=`

Control-plane (UI-facing):

- `GET /api/delivery/receipts?limit=&cursor=`

Inbox items now include:

- `delivery_state`
- `latest_receipt_id` (when receipts exist)
- `delivery_receipt_count` (watch-native inbox only)

Watch summary `observation` adds:

- `receipts_count`
- `last_receipt_at`
- `last_receipt_result`

## Events

Delivery attempts append canonical observation events:

- `delivery_attempted`
- `delivery_succeeded` or `delivery_failed`

Visible on `/internal/watch/events` and `/api/watch/events`.

## Verification

```bash
npm run verify:test5
# or
./scripts/verify/test5-delivery-receipts.sh
```

Unit tests:

- `tests/test_watch_delivery_receipts.py`
- `tests/test_control_plane_delivery_receipts.py`
- `tests/test_test5_delivery_receipts_acceptance.py` (live stack)

## UI proof

Attention sidebar (`AttentionStackPanel.vue`) shows a `DELIVERED` (or other
state) badge beside ranked signals when `delivery_state !== not_required`.

## Restart note

Restart **watch** and **control-plane** after route changes. TEST-5 restarts both
when the dev stack is already running.

## Cutover status

Locked cutover item **Delivery receipts for operator attention** — verified by TEST-5.

Next locked item: **KAIRO watch rules**.
