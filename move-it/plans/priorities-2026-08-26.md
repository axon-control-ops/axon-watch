# MoveIT priorities — 2026-08-26 (implementation started)

Lead: Jabulani
Run: implementation kickoff — first slice staged

## Now (dependency order)

1. **Promote staged code** — `sh output/deploy-first-slice.sh` when `services/`, `tests/`, `apps/` are writable (currently EROFS on Lead worker checkout).
2. **Reed** — contracts already implemented in `output/contract-work/`; land at `services/api/` + contract tests (16/16 pass in staging).
3. **Ayesha** — Expo app staged at `output/apps/customer/`; land at `apps/customer/`; wire mock getters to Reed modules after promote.
4. **Remy** — run `output/verification/run-first-slice-verify.sh`; sign off C1–C3 subset when promote + delivery pass.
5. **Sol** — no integration required for slice 1 (mock/local contracts only).

## Staged deliverables (verified this turn)

| Owner | Artifact | Status |
|---|---|---|
| Reed | `services/api/customer-home.js`, `job-confirmation.js`, `shared.js` | staged; 16/16 tests in mirror |
| Ayesha | `apps/customer/` Expo scaffold + Home + Confirmation screens | staged; tsc clean |
| Remy | `output/verification/first-slice-checklist.md` + verify script | prep in progress |

## Blocked

- **Canonical path write** — worker checkout read-only for `services/`, `tests/`, `apps/`, `lib/`.
- **P0-1 delivery** — still not configured; publish gate blocks commit until Mira completes `task-ce8d797d404d408c`.

## Done since last note

- First implementation slice **built in staging** (not planning-only).
- Dependency order enforced: Reed contracts → Ayesha screens → Remy verify.

## Explicit non-goals

- Live Tracking, Driver Dashboard, Operations screens
- External retailer integrations
- Sol connector work unless slice genuinely needs it
