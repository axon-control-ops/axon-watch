# Parity Closure Roadmap

## Purpose

Post-cutover plan for closing the **12 partially verified** must-keep behaviors in
`config/parity-snapshot.json` and clearing blockers for full axon-local retirement.

This is **Phase 2** work. The locked cutover checklist (`docs/AXON_X_CUTOVER_TODO.md`)
is complete. Do not reorder cutover items here.

**Source of truth:** `config/parity-snapshot.json`  
**Promotion rule:** contract + focused E2E + UI projection proof → update snapshot row to `verified`  
**Planning mirror:** sync `docs/planning/PARITY_LEDGER.md` after each promotion

## Lock rule

1. Execute slices in the locked order below unless the operator reprioritizes explicitly.
2. One slice per pass; run the slice gate before starting the next.
3. Do not mark `full_axon_local_retirement: true` until snapshot shows zero partial rows and blockers are empty.
4. Polish items belong in `docs/internal/AGENT-POLISH-NOTES.md`; parity promotion requires proof.

## Current state (2026-07-05)

| Metric | Value |
|---|---:|
| Verified (v1) | 15 |
| Partially verified | 4 |
| Phase A | **Complete** (P-A1–P-A4) |
| Phase B | **Complete** (P-B1–P-B3) |
| Phase C | **In progress** (P-C1–P-C2 done) |
| Next slice | **P-C3** |

Machine-readable order: `config/parity-closure-order.json`

---

## Phase A — Run-state trust

Highest leverage for operator confidence. Aligns with fitness functions: stop/resume
integrity, approval transition integrity, signal inbox consistency.

| ID | Parity row(s) | Deliverable | Gate |
|---|---|---|---|
| **P-A1** | `run_stop_resume` | Stop/resume cross-surface consistency: `/api/runs`, `/api/runtime/summary`, history receipts; mission-control projection tests | `npm run verify:parity-a1` |
| **P-A2** | `approval_boundaries` | Approve/reject boundary blocks resume/complete/commands until approve; cross-surface pending count | `npm run verify:parity-a2` |
| **P-A3** | `review_ready_state` | Review-ready cross-surface + resume/complete/command paths | `npm run verify:parity-a3` |
| **P-A4** | `signal_inbox_consistency` | Inbox/summary/briefing signal_id/severity/status/source agreement | `npm run verify:parity-a4` |

**Phase A E2E gate:** `npm run verify:phase-a` (runs P-A1–P-A4 checks + full verify once)

Phase A complete when all four slices are `done` and `next_slice` is **P-B1**.

**P-A1 spec:** `docs/PARITY_A1_RUN_STOP_RESUME.md`

---

## Phase B — Observability and boot discipline

| ID | Parity row(s) | Deliverable | Gate |
|---|---|---|---|
| **P-B1** | `initial_shell_boot_expectations` | Wire `shell_boot_readiness` report into verify; clear PENDING fitness | `npm run verify:parity-b1` |
| **P-B2** | `runtime_summary_behavior` | Runtime + watch summary latency samples in CI or nightly | `npm run verify:parity-b2` |
| **P-B3** | `runtime_summary_behavior` | Boot-critical field allowlist vs axon-local | `npm run verify:parity-b3` |

**Phase B E2E gate:** `npm run verify:phase-b` (runs P-B1–P-B3 checks + full verify once)

Phase B complete when all three slices are `done` and `next_slice` is **P-C1**.

**P-B1 spec:** `docs/PARITY_B1_INITIAL_SHELL_BOOT.md`

---

## Phase C — Operator presence (KAIRO v2)

| ID | Parity row(s) | Deliverable | Gate |
|---|---|---|---|
| **P-C1** | `kairo_persona_operator_copy` | Persisted persona settings; tone without run-truth drift | `npm run verify:parity-c1` |
| **P-C2** | `executive_operator_rhythm` | Richer Notice/Advise/Decide from canonical state | `npm run verify:parity-c2` |
| **P-C3** | `mobile_operator_cockpit_compactness` | Viewport resize reactivity + compact refetch | `verify:parity-c3` (TBD) |
| **P-C4** | `spoken_high_value_alerts` | Policy + optional voice-deck hook (browser TTS may remain fallback) | `verify:parity-c4` (TBD) |

---

## Phase D — Platform and retirement blockers

Required before **full** axon-local retirement, not before day-to-day Axon-X dev.

| ID | Parity row(s) | Deliverable | Gate |
|---|---|---|---|
| **P-D1** | (polish + dedicated) | SQLite persistence for watch commands/events/receipts | `verify:parity-d1` (TBD) |
| **P-D2** | delivery blockers | Real push/desktop/webhook adapters + retry | `verify:parity-d2` (TBD) |
| **P-D3** | dedicated blocker | Live dedicated-host smoke (not artifacts-only) | `verify:parity-d3` (TBD) |
| **P-D4** | multi-project blocker | Second bound workspace + child-project E2E | `verify:parity-d4` (TBD) |
| **P-D5** | voice blocker | Vue voice deck over events (replace Alpine polling) | `verify:parity-d5` (TBD) |
| **P-D6** | `dock_behavior`, `desktop_and_browser_startup` | Agent-dock parity + desktop startup contract or explicit browser-only decision | `verify:parity-d6` (TBD) |

---

## Per-slice workflow

1. Implement bounded module changes (no monolith growth).
2. Add spec under `docs/PARITY_*.md` when non-trivial.
3. Add gate script under `scripts/verify/parity-*.sh` and `npm run verify:parity-*`.
4. Update `config/parity-snapshot.json` row(s) to `verified` with evidence.
5. Update `docs/planning/PARITY_LEDGER.md` snapshot table.
6. Set slice `status: done` in `config/parity-closure-order.json`.
7. Sync axon-local mirror: `python3 scripts/ops/sync_planning_mirror_to_axon_local.py`
8. Run `npm run verify` before merge.

## Full retirement exit criteria

All must be true before amending `docs/CUTOVER_DECISION.md` to approve full retirement:

- `config/parity-snapshot.json` → `partially_verified` count is **0**
- `blockers_for_full_retirement` is **empty**
- Latency fitness budgets PASS or explicitly waived with expiry
- Operator sign-off on production switch from port 7734

## References

- Bounded cutover decision: `docs/CUTOVER_DECISION.md`
- Final audit: `docs/FINAL_PARITY_VERIFICATION.md`
- Fitness targets: `docs/planning/FITNESS_FUNCTIONS.md`
- Polish backlog: `docs/internal/AGENT-POLISH-NOTES.md`
