# Axon-X Cutover Decision

**Date:** 2026-07-05  
**Branch:** `axon-watch/dev`  
**Inputs:** `docs/FINAL_PARITY_VERIFICATION.md`, `config/parity-snapshot.json`, TEST-0 … TEST-9 gates

## Decision

### Bounded Axon-X cutover — **APPROVED**

Axon-X is approved as the **primary development surface** for:

- Console operator and IDE shell work (`apps/console-web/`)
- Control-plane and axon-watch service thin slices
- Cutover verification, planning, and parity tracking in this repo

Day-to-day Axon-X development should happen on **`axon-watch/dev`**, not by
expanding axon-local monolith hotspots for the same surfaces.

### Full axon-local retirement — **NOT APPROVED**

`axon-local` (port **7734**) **remains required** as the production reference
and fallback for:

- Live operator workflows not yet bound to Axon-X
- Child-project integration and legacy connector paths
- Full voice deck / JARVIS companion runtime
- Real delivery channels (push, desktop notifications, webhooks)
- Multi-project continuous development until workspace bindings mature

This follows the strangler model in `docs/planning/TRANSITION_ARCHITECTURE.md`.

## Parity summary

| Metric | Value |
|---|---:|
| Must-keep behaviors assessed | 19 |
| Verified for v1 scope | 8 |
| Partially verified | 11 |
| Full parity (unlimited axon-local equivalence) | 0 |

Partial verification is **expected** at this stage. TEST-N gates prove thin-slice
contracts; they do not prove unlimited axon-local replacement.

## Operating rules after cutover

1. **Implementation truth** lives in `axon-watch` (`docs/`, `docs/planning/`, code).
2. **axon-local** is fallback owner for unmigrated capabilities per transition table.
3. New console/operator features land in Axon-X bounded modules — not axon-local hotspots.
4. Promote a parity row to `verified` only with contract + focused E2E + UI proof.
5. Do not mark `full_axon_local_retirement` until all blockers in the parity snapshot are resolved.

## Rollback

Rollback is **capability-scoped**, not system-wide:

- If an Axon-X surface regresses, route that capability back to axon-local per
  `docs/planning/TRANSITION_ARCHITECTURE.md` rollback table.
- Keep TEST-0 … TEST-10 gates green before re-attempting a migrated capability.

## Blockers for full retirement

See `config/parity-snapshot.json` → `blockers_for_full_retirement`. Key items:

- 12 partially verified must-keep behaviors
- Real delivery channels and voice deck parity
- Dedicated-server live-host proof
- Latency fitness evidence PENDING in default verify
- Multi-project continuous development not validated on Axon-X alone

## Verification

```bash
npm run verify:test10
# or
./scripts/verify/test10-final-parity-cutover.sh
```

## Coordinator sign-off

This decision is recorded by the TEST-10 gate passing on 2026-07-05 with an
honest parity snapshot. Human operator may override operating rules but should
not treat this as unlimited axon-local retirement without a new assessment.
