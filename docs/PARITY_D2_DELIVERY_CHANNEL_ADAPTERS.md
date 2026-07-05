# P-D2 — Delivery Channel Adapters

## Deliverable

Real delivery channel adapters with retry for operator-attention signals.

## v1 scope

### In scope

- Bounded adapters under `services/axon-watch/app/delivery/adapters/`:
  - `inbox` — projection success
  - `desktop` — append JSONL notification under `AXON_WATCH_STATE_DIR`
  - `webhook` — POST to `AXON_WATCH_DELIVERY_WEBHOOK_URL`
  - `mobile_push` — POST to `AXON_WATCH_MOBILE_PUSH_URL`
  - `slack` — POST to `AXON_WATCH_SLACK_WEBHOOK_URL`
- Transient failure retry (`AXON_WATCH_DELIVERY_RETRY_MAX`, default 3)
- Optional channels auto-enrolled for `high` / `critical` when env URLs are set
- Contract checker: `scripts/verify/check_delivery_channel_adapters.py`

### Acceptable v1 degradation

- Adapters require operator-configured URLs; unconfigured optional channels are skipped
- Desktop uses file-based notification ledger, not OS-native notifications
- No FCM/APNs SDK integration

### Out of scope

- Live mobile push certificate provisioning
- Slack app OAuth install flow

## Gate

```bash
npm run verify:parity-d2
```

## Promotion

On gate pass, update `config/parity-closure-order.json` → `P-D2.status = done`,
`next_slice = P-D3`.
