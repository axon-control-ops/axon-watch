# Phase G5 — Gate Design (`verify:signal-parity-matrix`)

**Opened:** 2026-07-07  
**Status:** Design only — script stub optional after triage  

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
- TEST-3 step `[5/5]` and TEST-9 step `[4/4]` full verify hooks
- Headed Playwright / visual proof scripts (`.local/verify/g4-visual-proof/`)

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

Verified read-only 2026-07-07 via `python3 scripts/ops/planning_bundle_manifest.py validate`:

| Blocker | Symptom | Owner | Fix slice | Notes |
|---------|---------|-------|-----------|-------|
| **PLAN-MANIFEST-001** | `hash mismatch` for `IMPORT_MATRIX.md`, `IMPLEMENTATION_ROADMAP.md` | planning | **G5.0-triage** | Regenerate `docs/planning/MANIFEST.json` after planning edits |
| **PLAN-MANIFEST-002** | Untracked `agent-orchestration-contract.md` | planning | **G5.0-triage** | Add to MANIFEST or move under tracked path |
| **TEST3-FULL-VERIFY** | TEST-3 `[5/5]` invokes `npm run verify` | verify scripts | **G5.0-triage** | Replace step 5 with scoped bundle or `verify:signal-parity-matrix` |
| **TEST9-FULL-VERIFY** | TEST-9 `[4/4]` invokes `npm run verify` | verify scripts | **G5.0-triage** | Same as TEST-3 |
| **VAULT-TEST-ISOLATION** | Host Cursor OAuth can flake vault integration tests | cli_runtime | G2 maintenance | Document env guard; already noted in G3.7 append log |
| **DELIVERY-REGRESSION** | Operator reports delivery receipt failures in full verify | axon-watch + CP | **G5.0-triage** | Re-run `verify:test5` + `verify:parity-d2` in isolation; file ticket if red |

**Triage order:** PLAN-MANIFEST → decouple TEST-3/9 from full verify → re-run `verify:signal-parity-matrix` candidate.

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
