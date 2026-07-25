# P-A3 — Review-Ready State Cross-Surface Parity

## Parity row

`review_ready_state` in `config/parity-snapshot.json`

## Verification method (from ledger)

Canonical `review_ready` transition + UI review state visible in dock and run summary.

## v1 scope

### In scope

- `POST /review-ready` from `executing` → `review_ready` with `review_ready` receipt.
- Cross-surface while in review: `/api/runs`, `/api/runtime/summary`, `/api/briefing`
  agree on phase/status and keep run active.
- `POST /resume` from `review_ready` → `executing` with receipt.
- `POST /complete` from `review_ready` → `completed`.
- `execute_resume_from_review` command path for workspace-scoped resume.
- Mission control projections show `REVIEW READY` phase and review affordances.

### Acceptable v1 degradation

- No apply/discard UI parity with axon-local.
- Browser click E2E deferred.

## Gate

```bash
npm run verify:parity-a3
```

Next slice: **P-A4** (`signal_inbox_consistency`).
