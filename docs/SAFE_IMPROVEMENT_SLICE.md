# Safe Improvement — First Vertical Slice

**Status:** Implemented (control-plane slice; disposable worktree sandbox)
**Tracker:** [`AUTONOMY_RELIABILITY_TRACKER.md`](AUTONOMY_RELIABILITY_TRACKER.md) item 8
**Package:** `services/control-plane/app/safe_improvement/`
**Contract:** [`SELF_IMPROVEMENT_CONTRACT.md`](SELF_IMPROVEMENT_CONTRACT.md)

## Goal

Provide an honest, gated self-improvement loop: capture a redacted trace, evaluate
a proposal against a named threshold in an **isolated disposable checkout**, require
an **exact-effect** approval for policy/secret/production/merge effects, execute only
after approval, and support rollback with receipts.

No agent may silently mutate policy, secrets, production, or merge targets.

## Effect taxonomy (exact approval required)

| Effect       | Meaning in this slice                                                     |
| ------------ | ------------------------------------------------------------------------- |
| `merge`      | Promote a candidate change after verification (inside disposable root)    |
| `policy`     | Reserved; same fingerprint gate                                           |
| `secret`     | Reserved; same fingerprint gate                                           |
| `production` | Reserved; same fingerprint gate                                           |

Generic Full Access / run approvals **cannot** substitute for an `eap_*`
exact-effect approval bound to the proposal fingerprint.

## API

Prefix: `/api/safe-improvement`

- `POST /traces` — capture redacted trace + receipt refs
- `POST /cases` — upsert evaluation case (metric + threshold + comparator)
- `POST /proposals` — draft proposal linked to trace + case
- `POST /proposals/{id}/evaluate` — disposable checkout + threshold check
- `POST /proposals/{id}/request-approval` — bind fingerprint + expiry
- `POST /proposals/{id}/approve` — must present exact `effect_fingerprint`
- `POST /proposals/{id}/execute` — isolated merge promote + receipt
- `POST /proposals/{id}/rollback` — restore baseline sidecar, cleanup checkout + receipt
- `GET /proposals` / `GET /proposals/{id}` — evidence listing

## Thresholds

Comparator `lte` (default): candidate − baseline must be `<= threshold`.
A regression beyond the threshold fails the proposal (`status=failed`).

Thresholds cannot be silently loosened by execution; they live on the case
record and are re-read at evaluation time.

## Isolation rule

`isolated_executor` creates a temporary proposal parent (`axon-si-…`) and a
disposable checkout via git worktree (preferred) or local clone, pinned to the
bound project's HEAD commit. Sidecar markers/metrics live under `.axon-si/`.
Bound workspace roots are never written during evaluate/execute/rollback.
Creation failure fails closed (no write to the bound root).

Agent assist during evaluation must use `proposal_service.sandbox_agent_workspace`
(or `isolated_executor.agent_workspace_for_isolation`) so cwd/workspace points at
the disposable root only.

## Verification

```bash
./scripts/dev/python.sh -m unittest tests.test_safe_improvement -v
./scripts/dev/python.sh -m unittest tests.test_safe_improvement_gate -v
```

Included in `scripts/verify/run_contract_unit_tests.sh`.

## Session enablement

Default-off. Enable for a bounded session with either:

- Composer mode menu → **Enable Sandbox** (calls `POST /api/safe-improvement/session/enable`), or
- `AXON_SAFE_IMPROVEMENT_ENABLED=1` for process-wide force-on

`GET /api/safe-improvement/session` reports `{ enabled, session_enabled, env_forced, source }`.
Proposal routes return 404 until enabled. Turn Sandbox off from the same menu
(or unset the env var) when the session ends.

## Deferred

- Broad evaluation datasets / training
- Automatic policy or secret mutation
- Real merge / push of sandbox results into the live bound branch
- Docker / process enclosure (`infra/docker/` packaging)
- Full console proposal projector (session toggle ships; proposal list UI follow-up)
