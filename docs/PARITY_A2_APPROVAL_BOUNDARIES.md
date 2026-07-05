# P-A2 — Approval Boundaries Cross-Surface Parity

## Parity row

`approval_boundaries` in `config/parity-snapshot.json`

## Verification method (from ledger)

Contract test on approval phase + UI proof that approval blocks execution
everywhere consistently.

## v1 scope

### In scope

- `requires_approval` run enters `awaiting_approval` with `can_approve=true`,
  `can_resume=false`.
- **Blocked until approve:** `POST /resume`, `POST /complete`, and chat command
  execution (`orchestrate_command_run` only runs in `executing` phase).
- Cross-surface consistency while pending:
  - `/api/runs/{id}` and `/api/runs` list
  - `/api/runtime/summary` `active_runs[0]` + `approvals.pending_count`
  - `/api/briefing` `pending_approvals` + `next_safe_actions` (`approve_run`)
- After **approve:** surfaces show `executing`, pending count `0`, `operator_approve`
  receipt.
- After **reject:** run terminal `cancelled`, pending count `0`, `operator_reject`
  receipt.
- Mission control + run-selection projections surface approval state and pending
  approval count.

### Acceptable v1 degradation

- Reduced approval presentation polish vs axon-local.
- Browser click E2E deferred (same as P-A1).

### Out of scope

- Every legacy axon-local guarded action type
- Persistent approval preference store

## Gate

```bash
npm run verify:parity-a2
```

## Promotion

On gate pass, update snapshot row to `verified` and set `P-A2.status = done`.

Next slice: **P-A3** (`review_ready_state`).
