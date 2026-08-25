# Axon-X Cutover Decision

**Date:** 2026-07-05  
**Last amended:** 2026-08-25 (axon-local runtime retirement)
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

### Full axon-local runtime retirement — **APPROVED**

`axon-local` is no longer an active fallback, workspace binding, proxy target, or
startup dependency from this repo. Axon-X owns day-to-day operator work directly.

**Production operator surface (declared 2026-07-05):** Axon-X console-web at
**http://127.0.0.1:4173**. See `docs/PRODUCTION_OPERATOR_SURFACE.md`.

WhatsApp can be revisited later as a fresh Axon-X feature. That future work must
not require restarting `axon-local` from this repo.

## Parity summary

| Metric | Value (post Phase A–D) |
|---|---:|
| Must-keep behaviors assessed | 19 |
| Verified for v1 scope | 19 |
| Partially verified | 0 |
| Full parity (unlimited axon-local equivalence) | 0 |

All must-keep behaviors meet **v1 verification** within documented acceptable
degradation. The remaining accepted degradations are Axon-X-owned or future work,
not `axon-local` fallback obligations.

## Operating rules after cutover

1. **Implementation truth** lives in `axon-watch` (`docs/`, `docs/planning/`, code).
2. **axon-local** must not be started, proxied, or listed as an active fallback by this repo.
3. New console/operator features land in Axon-X bounded modules — not axon-local hotspots.
4. Promote a parity row to `verified` only with contract + focused E2E + UI proof.
5. Reopen WhatsApp later as an Axon-X feature, not as a hidden dependency on the retired runtime.

## Rollback

Rollback is **capability-scoped**, not system-wide:

- If an Axon-X surface regresses, fix or disable that Axon-X capability directly.
- Keep TEST-0 … TEST-10 and `npm run verify:phase-d` green before re-attempting a migrated capability.

## Blockers for full retirement

See `config/parity-snapshot.json` → `blockers_for_full_retirement`.

As of production operator declaration (2026-07-05):

- **Resolved:** operator sign-off — Axon-X `:4173` is the production operator surface

Remaining for **full** axon-local runtime retirement:

- None. `config/parity-snapshot.json` has `full_axon_local_retirement: true`.

Resolved since initial TEST-10 assessment (no longer blockers):

- Partially verified must-keep behaviors (0 remaining)
- Operator production switch to Axon-X `:4173` (declared 2026-07-05)
- Voice deck / spoken-alert v1 parity (P-D5)
- Dedicated-host smoke at v1 scope (P-D3 simulated; live host optional)
- Multi-project dual-workspace proof (P-D4)
- Delivery channel adapters at v1 scope (P-D2)
- Latency fitness budgets in default verify

## Verification

```bash
npm run verify:test10
npm run verify:phase-d
npm run verify:production-operator
# or
./scripts/verify/test10-final-parity-cutover.sh
./scripts/verify/phase-d-platform-retirement.sh
./scripts/verify/production-operator-smoke.sh
```

## Coordinator sign-off

Initial decision recorded by TEST-10 passing on 2026-07-05 (bounded cutover,
honest partial snapshot at that time).

**Amendment (2026-07-05):** Production operator surface declared — Axon-X
`:4173` is primary; `:7734` was fallback only.

**Amendment (2026-08-25):** axon-local runtime retirement approved. This repo no
longer starts, proxies, binds, or documents `axon-local` as an active fallback.
WhatsApp is deferred for a future Axon-X-native revisit.

Human operator may override operating rules but should not treat v1 parity
closure as permission to reintroduce a hidden `axon-local` runtime dependency.
