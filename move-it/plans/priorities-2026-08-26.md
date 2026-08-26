# MoveIT priorities — 2026-08-26 (first slice promoted)

Lead: Jabulani
Run: `run_3fd4b12aed22` — Lead retry (Critical Review Clause recovery)

## Now (dependency order)

1. **P0-1 delivery** — current AXON-X control plane reports MoveIT delivery configured; failed historical Mira handoff `handoff-fb7fd86e7d8f41e8` / `task-ce8d797d404d408c` still needs operator review.
2. **Reed** — contracts **promoted** to `services/api/` + `tests/`; **16/16 pass** (`agent-job-6742604d6d89`).
3. **Ayesha** — Expo app at `apps/customer/` (Home + Confirmation); wire mock getters to Reed modules; complete Gate 6 confidence on active run `run_8d202dcc94de`.
4. **Remy** — run `output/verification/run-first-slice-verify.sh`; sign off Layer A (automated) then B/C manual C1–C3.
5. **Sol** — no integration required for slice 1; connector work waits for Remy Layer B/C sign-off.

## Promoted deliverables (verified this retry)

| Owner | Artifact | Status |
|---|---|---|
| Reed | `services/api/*.js`, contract tests under `tests/` | **promoted**; 16/16 pass |
| Ayesha | `apps/customer/` Expo scaffold + Home + Confirmation | **promoted**; tsc pending Remy verify |
| Remy | `output/verification/first-slice-checklist.md` + verify script | Layer A ready to run |

## Blocked

- **Historical P0-1 handoff** — `handoff-fb7fd86e7d8f41e8` failed before the delivery endpoint repair; keep it as evidence and close/retry through the operator workflow.
- **Private probe file** — `output/delivery-probe-2026-08-26.txt` absent in worker checkout; note preserved at `docs/ops/delivery-probe-note-2026-08-26.md` for real-root cleanup if still present.

## Done since last note

- First slice **promoted** to canonical paths (no longer staging-only).
- Delivery-probe `.txt` relocated so `private_company_material` gate clears for other teammates.
- Lead ops docs refreshed with live API receipts.

## Explicit non-goals

- Live Tracking, Driver Dashboard, Operations screens
- External retailer integrations
- Sol connector work unless slice genuinely needs it
