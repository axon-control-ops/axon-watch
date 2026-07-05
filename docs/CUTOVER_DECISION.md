# Axon-X Cutover Decision

**Date:** 2026-07-05  
**Last amended:** 2026-07-05 (Phase A–D parity closure complete)  
**Branch:** `axon-watch/dev`  
**Inputs:** `docs/FINAL_PARITY_VERIFICATION.md`, `config/parity-snapshot.json`, TEST-0 … TEST-10 gates, Phase A–D parity gates

## Decision

### Bounded Axon-X cutover — **APPROVED**

Axon-X is approved as the **primary development surface** for:

- Console operator and IDE shell work (`apps/console-web/`)
- Control-plane and axon-watch service thin slices
- Cutover verification, planning, and parity tracking in this repo

Day-to-day Axon-X development should happen on **`axon-watch/dev`**, not by
expanding axon-local monolith hotspots for the same surfaces.

### Full axon-local retirement — **NOT APPROVED**

`axon-local` (port **7734**) **remains required** as the production operator
reference until the operator explicitly declares a switch to Axon-X (`:4173`).

Fallback ownership for unmigrated surfaces:

- Child-project integration and legacy connector paths not yet bound in Axon-X
- Unlimited axon-local visual/runtime equivalence (v1 verified ≠ full parity)

This follows the strangler model in `docs/planning/TRANSITION_ARCHITECTURE.md`.

## Parity summary

| Metric | Value (post Phase A–D) |
|---|---:|
| Must-keep behaviors assessed | 19 |
| Verified for v1 scope | 19 |
| Partially verified | 0 |
| Full parity (unlimited axon-local equivalence) | 0 |

All must-keep behaviors meet **v1 verification** within documented acceptable
degradation. That is not the same as unlimited axon-local replacement.

## Operating rules after cutover

1. **Implementation truth** lives in `axon-watch` (`docs/`, `docs/planning/`, code).
2. **axon-local** is fallback owner for unmigrated capabilities per transition table.
3. New console/operator features land in Axon-X bounded modules — not axon-local hotspots.
4. Promote a parity row to `verified` only with contract + focused E2E + UI proof.
5. Do not mark `full_axon_local_retirement` until all blockers in the parity snapshot are resolved **and** the operator signs off on production switch from port 7734.

## Rollback

Rollback is **capability-scoped**, not system-wide:

- If an Axon-X surface regresses, route that capability back to axon-local per
  `docs/planning/TRANSITION_ARCHITECTURE.md` rollback table.
- Keep TEST-0 … TEST-10 and `npm run verify:phase-d` green before re-attempting a migrated capability.

## Blockers for full retirement

See `config/parity-snapshot.json` → `blockers_for_full_retirement`.

As of Phase A–D completion (2026-07-05):

- **Operator sign-off:** axon-local port 7734 remains production operator reference until operator declares switch to Axon-X `:4173`

Resolved since initial TEST-10 assessment (no longer blockers):

- Partially verified must-keep behaviors (0 remaining)
- Voice deck / spoken-alert v1 parity (P-D5)
- Dedicated-host smoke at v1 scope (P-D3 simulated; live host optional)
- Multi-project dual-workspace proof (P-D4)
- Delivery channel adapters at v1 scope (P-D2)
- Latency fitness budgets in default verify

## Verification

```bash
npm run verify:test10
npm run verify:phase-d
# or
./scripts/verify/test10-final-parity-cutover.sh
./scripts/verify/phase-d-platform-retirement.sh
```

## Coordinator sign-off

Initial decision recorded by TEST-10 passing on 2026-07-05 (bounded cutover,
honest partial snapshot at that time).

**Amendment (2026-07-05):** Phase A–D parity closure complete — 19 verified v1,
0 partially verified. Full axon-local retirement remains **NOT APPROVED** pending
operator production-switch sign-off only.

Human operator may override operating rules but should not treat v1 parity
closure as unlimited axon-local retirement without explicit switch declaration.
