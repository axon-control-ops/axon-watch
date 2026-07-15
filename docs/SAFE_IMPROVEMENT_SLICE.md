# Safe Improvement — First Vertical Slice

**Status:** Implemented (control-plane slice)
**Tracker:** [`AUTONOMY_RELIABILITY_TRACKER.md`](AUTONOMY_RELIABILITY_TRACKER.md) item 8
**Package:** `services/control-plane/app/safe_improvement/`

## Goal

Provide an honest, gated self-improvement loop: capture a redacted trace, evaluate
a proposal against a named threshold in an **isolated** workspace, require an
**exact-effect** approval for policy/secret/production/merge effects, execute only
after approval, and support rollback with receipts.

No agent may silently mutate policy, secrets, production, or merge targets.

## Effect taxonomy (exact approval required)

| Effect       | Meaning in this slice                                           |
| ------------ | --------------------------------------------------------------- |
| `merge`      | Promote a candidate change after verification (isolated marker) |
| `policy`     | Reserved; same fingerprint gate                                 |
| `secret`     | Reserved; same fingerprint gate                                 |
| `production` | Reserved; same fingerprint gate                                 |

Generic Full Access / run approvals **cannot** substitute for an `eap_*`
exact-effect approval bound to the proposal fingerprint.

## API

Prefix: `/api/safe-improvement`

- `POST /traces` — capture redacted trace + receipt refs
- `POST /cases` — upsert evaluation case (metric + threshold + comparator)
- `POST /proposals` — draft proposal linked to trace + case
- `POST /proposals/{id}/evaluate` — isolated candidate change + threshold check
- `POST /proposals/{id}/request-approval` — bind fingerprint + expiry
- `POST /proposals/{id}/approve` — must present exact `effect_fingerprint`
- `POST /proposals/{id}/execute` — isolated merge promote + receipt
- `POST /proposals/{id}/rollback` — restore baseline marker/metric + receipt
- `GET /proposals` / `GET /proposals/{id}` — evidence listing

## Thresholds

Comparator `lte` (default): candidate − baseline must be `<= threshold`.
A regression beyond the threshold fails the proposal (`status=failed`).

Thresholds cannot be silently loosened by execution; they live on the case
record and are re-read at evaluation time.

## Isolation rule

`isolated_executor` creates a temporary proposal root. Bound workspace roots are
never written during evaluate/execute/rollback in this slice.

## Verification

```bash
./scripts/dev/python.sh -m unittest tests.test_safe_improvement -v
```

Included in `scripts/verify/run_contract_unit_tests.sh`.

## Deferred

- Broad evaluation datasets / training
- Automatic policy or secret mutation
- Real git worktree merge into bound workspaces
- Console UI projector (follow-up after API stability)
