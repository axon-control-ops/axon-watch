# Axon-Watch Planning Bundle

**Canonical home:** `axon-watch/docs/planning/` (migrated 2026-07-05).

This directory is the implementation-repo source of truth for product thesis,
contracts, parity tracking, and migration planning. Cutover work in
`docs/AXON_X_CUTOVER_TODO.md` defers here instead of split-brain references
into `axon-local`.

## Legacy mirror

`axon-local/Plans/Axon-Watch/` remains a continuity mirror for operators still
working in the production Axon repo. When planning changes land here, sync the
mirror with:

```bash
python3 scripts/ops/sync_planning_mirror_to_axon_local.py
```

## Documents

- `PRODUCT.md` — product thesis, journeys, non-goals
- `ARCHITECTURE.md` — service boundaries and deployment modes
- `UI_SPEC.md` — integrated shell layout and interaction model
- `UI_REFERENCE_ARCHETYPES.md` — command-center / JARVIS references
- `UI_COMPOSITION_SPEC.md` — topbar, status bar, dock, KAIRO composition
- `UI_VISUAL_DIRECTION.md` — visual north star and HUD chrome
- `run-state.md` — canonical run lifecycle and stop/resume rules
- `signal-events.md` — signal envelope, inbox ranking, delivery receipts
- `KAIRO_MODE.md` — KAIRO operator-presence research
- `KAIRO_BRAIN_UI_ARCHITECTURE.md` — JARVIS pack mapping, Operator vs IDE subscriptions (UI deferred)
- `OPERATOR_REFRESH_POLICY.md` — anti-freeze refresh rules (G4.4 guards)
- `agent-orchestration-contract.md` — G3 orchestration contract (add to MANIFEST on triage)
- `watch-api.md` — internal watch ↔ control-plane contract
- `control-api.md` — control-plane public API contract
- `runtime-summary.md` — runtime identity and watch-backed summaries
- `ADR-001` … `ADR-005` — architecture decision records
- `ADR_GOVERNANCE.md` — ADR lifecycle rules
- `IMPLEMENTATION_ROADMAP.md` — staged build order
- `IMPORT_MATRIX.md` — adopt/adapt/rewrite/discard rules from axon-local
- `REPO_BOOTSTRAP_SPEC.md` — initial scaffold blueprint
- `PARITY_LEDGER.md` — must-keep behaviors and verification status
- `FITNESS_FUNCTIONS.md` — architecture guardrails and budgets
- `TRANSITION_ARCHITECTURE.md` — strangler seam and rollback model
- `CONTRACT_TESTING_SPEC.md` — executable compatibility rules
- `DELIVERY_PLAN.md` — reviewable slice sequencing
- `TEST_STRATEGY.md` — contract/UI/service/E2E test layers
- `SERVER_DEPLOYMENT_SPEC.md` — dedicated-server topology

## Doc split

- **Frozen planning (this folder):** product thesis, contracts, migration, KAIRO
  research, visual north star, parity ledger.
- **Implementation authority (`docs/` outside this folder):** locked layout
  (`UI_LAYOUT_LOCK.md`, ADR-004 layout), implementation ADRs 001–008, handbook,
  multitask lanes, thin-slice specs (`WORKSPACE_*`, `WATCH_*`, etc.), Phase G
  tracks (`PHASE_G_SIGNAL_PARITY.md`, `PHASE_G5_*`, `PHASE_G6_*`).

When implementation diverges from planning, amend planning docs here — do not
delete history. Layout geometry remains locked in
`docs/adr/ADR-004-locked-console-shell-layout.md`.

## Integrity

`MANIFEST.json` records sha256 hashes for every `.md` file in this directory.
Regenerate after intentional edits:

```bash
python3 scripts/ops/planning_bundle_manifest.py write
python3 scripts/ops/planning_bundle_manifest.py validate
```
