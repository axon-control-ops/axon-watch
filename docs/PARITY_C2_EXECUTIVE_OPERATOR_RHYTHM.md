# P-C2 — Executive Operator Rhythm

## Parity row

`executive_operator_rhythm` in `config/parity-snapshot.json`

## Verification method (from ledger)

Briefing API returns Notice/Advise/Decide/Execute/Verify/Report shaped summary
from canonical state.

## v1 scope

### In scope

- `/api/briefing` includes `executive_rhythm` with all six rhythm keys.
- Top-level `notice` / `advise` mirror `executive_rhythm.notice` / `.advise`.
- `decide`, `execute`, `verify`, `report` derive from pending approvals, active
  runs, top signals, degraded state, and `next_safe_actions` — not invented truth.
- Contract checker: `scripts/verify/check_executive_operator_rhythm.py`
- UI projection: BriefingPanel rhythm sections + mission-control Decide line.

### Acceptable v1 degradation

- Rhythm strings are template-based, not full axon-local narrative richness.
- No separate `/api/executive-rhythm` route; rhythm rides on briefing only.

### Out of scope

- Full `executive_operator_workflow.py` plan-step generation
- Chat/voice orchestration hooks for each rhythm phase

## Gate

```bash
npm run verify:parity-c2
```

## Promotion

On gate pass, update:

- `config/parity-snapshot.json` → `executive_operator_rhythm.status = verified`
- `docs/planning/PARITY_LEDGER.md` snapshot table
- `config/parity-closure-order.json` → `P-C2.status = done`

Next slice: **P-C3** (`mobile_operator_cockpit_compactness`).
