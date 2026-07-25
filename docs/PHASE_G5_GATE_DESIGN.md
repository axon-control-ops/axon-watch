# Phase G5 — Gate Design (`verify:signal-parity-matrix`)

**Opened:** 2026-07-07  
**Status:** Implemented — `verify:signal-parity-matrix` (TEST-26) green on `dev` 2026-07-07

## Purpose

Define the **G5 exit gate** composition without requiring full `npm run verify` until known blockers are triaged. Implementation agent adds `scripts/verify/test26-signal-parity-matrix.sh` (or amends `package.json`) when ready.

## Proposed npm script

```json
"verify:signal-parity-matrix": "./scripts/verify/test26-signal-parity-matrix.sh"
```

## Gate composition (ordered)

| Step | Script / command | Proves |
|------|------------------|--------|
| 1 | `npm run verify:contracts` | Shared DTOs + control-plane/watch contract tests |
| 2 | `npm run verify:console-web` | Typecheck + vitest + build (no headed browser) |
| 3 | `npm run verify:vault-parity` | G1 Vault II |
| 4 | `npm run verify:runtime-vault-integration` | G2 |
| 5 | `npm run verify:agent-orchestration-parity` | G3 |
| 6 | `npm run verify:connector-parity` | G4 bundle (TEST-25) — **not** full verify |
| 7 | `npm run verify:phase-a` | Run-state trust (P-A1–A4 bundle) |
| 8 | `npm run verify:phase-b` | Boot + runtime latency |
| 9 | `npm run verify:phase-d` | Platform retirement slice (watch persistence, delivery, dock) |
| 10 | `npm run verify:production-operator` | Production operator smoke |
| 11 | `python3 scripts/ops/planning_bundle_manifest.py validate` | Planning manifest in sync |
| 12 | Doc check: `docs/PHASE_G5_CAPABILITY_MATRIX.md` exists | G5.1 |

**Explicitly excluded from G5 gate (until triaged):**

- `npm run verify` monolith (runs `all.py` + full matrix)
- Headed Playwright / visual proof scripts (`.local/verify/g4-visual-proof/`)

**Resolved in G5.0-triage (2026-07-07):**

- PLAN-MANIFEST: `docs/planning/MANIFEST.json` validates (32 files)
- TEST-3 step `[5/5]` → scoped `verify:connector-parity`
- TEST-9 step `[4/4]` → scoped `verify:contracts`

**Headed browser smoke (Phase G6):** `npm run verify:headed-browser-smoke` — Playwright shell/operator/IDE checks + screenshots under `.local/verify/headed-smoke/`. Use `AXON_HEADED=1` for visible browser.

## Relationship to existing gates

```text
verify:signal-parity-matrix
  ├── verify:contracts
  ├── verify:console-web
  ├── Phase G backend gates (G1–G4)
  ├── Phase A/B/D parity bundles
  ├── verify:production-operator
  └── planning manifest validate
```

**Does not replace** G6 operator sign-off — human one-week `:4173`-only dry-run remains mandatory.

## Known failures blocking full `npm run verify`

The G5 gate (`verify:signal-parity-matrix`) intentionally avoids the full monolith. Remaining `npm run verify` blockers should be triaged separately if full monolith green is required.

| Blocker | Status (2026-07-07) | Notes |
|---------|----------------------|-------|
| **PLAN-MANIFEST-001/002** | **Resolved** | Manifest validates; `agent-orchestration-contract.md` tracked |
| **TEST3-FULL-VERIFY** | **Resolved** | TEST-3 step 5 → `verify:connector-parity` |
| **TEST9-FULL-VERIFY** | **Resolved** | TEST-9 step 4 → `verify:contracts` |
| **VAULT-TEST-ISOLATION** | Open (env) | Host Cursor OAuth can flake vault tests — document env guard |
| **DELIVERY-REGRESSION** | Triage if red | Re-run `verify:test5` + `verify:parity-d2` in isolation |

## G5.2 extended regression (manual + automated)

When `verify:signal-parity-matrix` is green:

1. `./scripts/dev/up.sh --no-open`
2. `./scripts/verify/production-operator-smoke.sh`
3. Manual `:4173` path: workspace_smoke → operator command → IDE agent turn → stop → Attention inbox
4. Optional: `./scripts/dev/collect-verify-evidence.sh` for artifact bundle

Record results in `docs/PHASE_G_EXECUTION_TRACK.md` append log.

## Stub script spec (`test26-signal-parity-matrix.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
# [1/N] npm run verify:contracts
# [2/N] npm run verify:console-web
# ... (steps 3–12 from table above)
# Do NOT call npm run verify
echo "TEST-26 PASS"
```

Add to root `package.json` only when triage complete.

## Acceptance

G5 gate design is complete when:

- This doc is linked from `PHASE_G_SIGNAL_PARITY.md` G5 section
- Triage table has owner per blocker
- Implementation agent can add TEST-26 without ambiguity
