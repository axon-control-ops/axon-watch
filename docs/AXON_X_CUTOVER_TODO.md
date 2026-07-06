# Axon-X Cutover TODO

## Purpose

This is the locked, append-only working report for replacing `axon-local` with
Axon-X for continuous development.

Use this file for cutover readiness only.

Source inputs:

- implementation truth: `docs/MULTITASK-LANES.md`
- target parity: `docs/planning/PARITY_LEDGER.md`
- roadmap context: `docs/planning/IMPLEMENTATION_ROADMAP.md`
- migration spec: `docs/CROSS_REPO_PLANNING_MIGRATION.md`

## Lock Rule

1. Do **not** reorder the checklist below.
2. Do **not** silently remove items.
3. Only mark an item done when it is verified in code, tests, or manual proof.
4. New discoveries go into the append log; they do not reshuffle the order.
5. Changing the order requires explicit user or coordinator approval.

## Current Readiness

Axon-X is approved for **bounded primary development** on `axon-watch/dev`
(console shell, control-plane, axon-watch thin slices). See
`docs/CUTOVER_DECISION.md`.

**Parity closure (Phase A–D) is complete:** 19 verified v1, 0 partially verified
(as of 2026-07-05). See `docs/PARITY_CLOSURE_ROADMAP.md` and
`npm run verify:phase-d`.

Axon-X is **not approved** for **full axon-local retirement** until child-project
and legacy connector surfaces are migrated (see `blockers_for_full_retirement`).

**Production operator surface:** http://127.0.0.1:4173 (declared 2026-07-05).
See `docs/PRODUCTION_OPERATOR_SURFACE.md` and `npm run verify:production-operator`.

## Already Landed

- [x] Three-service Axon-X stack (`:4173`, `:8787`, `:8788`)
- [x] Shared DTO contract baseline
- [x] Monaco file editing on workspace files
- [x] PTY terminal attachment
- [x] Workspace-scoped chat thread rehydration
- [x] Canonical run basics: stop / resume / approve / reject / review-ready
- [x] Bounded command executor (`read`, `list`, `git status`, resume-from-review)
- [x] Runtime summary / inbox / briefing / Notice-Advise path
- [x] Shell boot and latency evidence
- [x] Operator / IDE shell split, Attention sidebar, mission control work

## Locked Cutover Order

- [x] `TEST-0` manual acceptance on `workspace_smoke`
  Verified 2026-07-05 via `./scripts/verify/test0-workspace-smoke.sh` (health, mission-control unit tests, live API acceptance, `npm run verify`).

- [x] Real project/workspace connection
  Verified 2026-07-05 via `./scripts/verify/test1-workspace-project-connection.sh`
  (bindings config, workspace catalog enrichment, terminal/command cwd bridge,
  live `git status` in `workspace_axon_local`). Spec: `docs/WORKSPACE_PROJECT_CONNECTION.md`.

- [x] Workspace handoff slice
  Verified 2026-07-05 via `./scripts/verify/test2-workspace-handoff.sh`
  (`POST/GET /api/workspaces/{id}/handoffs`, persisted record, target workspace
  summary). Spec: `docs/WORKSPACE_HANDOFF.md`.

- [x] Watch connectors
  Verified 2026-07-05 via `./scripts/verify/test3-watch-connectors.sh`
  (config probes, watch summary/connectors routes, runtime summary projection,
  required-connector inbox signals). Spec: `docs/WATCH_CONNECTORS.md`.

- [x] Watch command / event / status depth
  Verified 2026-07-05 via `./scripts/verify/test4-watch-command-event-depth.sh`
  (`reprobe_connector`, `refresh_summary`, events log, summary `observation`,
  control-plane `/api/watch/commands|events`). Spec: `docs/WATCH_COMMAND_EVENT_DEPTH.md`.

- [x] Delivery receipts for operator attention
  Verified 2026-07-05 via `./scripts/verify/test5-delivery-receipts.sh`
  (severity routing, receipt store, inbox `delivery_state`, `/api/delivery/receipts`,
  Attention sidebar badge). Spec: `docs/DELIVERY_RECEIPTS.md`.

- [x] KAIRO watch rules
  Verified 2026-07-05 via `./scripts/verify/test6-kairo-watch-rules.sh`
  (`watch_rule` on inbox items, observe/advise/approval/execute mapping,
  Attention mode chip). Spec: `docs/KAIRO_WATCH_RULES.md`.

- [x] Spoken alerts, persona, and mobile presence
  Verified 2026-07-05 via `./scripts/verify/test7-operator-presence.sh`
  (`operator_presence` on `/api/briefing`, spoken-alert eligibility, persona
  voice line, mobile compact shell). Spec: `docs/OPERATOR_PRESENCE.md`.

- [x] Dedicated-server readiness
  Verified 2026-07-05 via `./scripts/verify/test8-dedicated-server-readiness.sh`
  (deployment topology, env validation, systemd/Caddy/compose artifacts,
  config-driven readiness). Spec: `docs/DEDICATED_SERVER_READINESS.md`.

- [x] Cross-repo planning migration
  Verified 2026-07-05 via `./scripts/verify/test9-cross-repo-planning-migration.sh`
  (canonical bundle in `docs/planning/`, `MANIFEST.json` integrity, axon-local
  continuity mirror sync script). Spec: `docs/CROSS_REPO_PLANNING_MIGRATION.md`.

- [x] Final parity verification and cutover decision
  Verified 2026-07-05 via `./scripts/verify/test10-final-parity-cutover.sh`
  (parity snapshot: 7 verified v1, 12 partially verified; bounded cutover
  approved, full axon-local retirement not approved).
  Spec: `docs/FINAL_PARITY_VERIFICATION.md`, `docs/CUTOVER_DECISION.md`.

## Append Log

Append new entries here in reverse-chronological order. Do not rewrite history.

### 2026-07-05 — Initial Progress closed, Phase F opened

- Axon-X remains approved for **bounded primary development** on `dev`.
- Treat the completed planning/bootstrap/parity/cutover/Phase E body of work as
  **Initial Progress COMPLETE**.
- Follow-on build work now moves to `docs/PHASE_F_OPERATOR_FOUNDATION.md`.
- Full axon-local retirement remains **not approved** pending Phase F closure and
  the later E6/F6 readiness review.

### 2026-07-05 — Phase E0–E5 (post-production operator)

- **Phase E** slices E0–E5 complete; **E6 paused** for final retirement review.
- Command plane: TEST-11 shell gate (`npm run verify:shell-commands`), `check-health` /
  `verify` shortcuts, Mission Control Connectors rail with reprobe/refresh and `:7734` fallback.
- Third workspace binding: `workspace_dashpro` (DashPro) with `npm run verify:child-project`.
- Watch inbox: bootstrap `signal_runtime_summary_degraded` omitted when required connectors trusted.
- Gates: `npm run verify:production-operator` PASS, `npm run verify:phase-d` PASS, TEST-11 + child-project live PASS.
- Docs: `docs/TRANSITION_PHASE_E_TODO.md`, `docs/LEGACY_CONNECTOR_INVENTORY.md`, handbook/starter updates.
- Full axon-local retirement **still not approved** — see E6 in Phase E checklist.

### 2026-07-05 — Production operator surface declared

- **Production operator:** Axon-X console-web at `http://127.0.0.1:4173`.
  axon-local `:7734` demoted to fallback for legacy connectors.
- Gate: `npm run verify:production-operator`
- Docs: `docs/PRODUCTION_OPERATOR_SURFACE.md`, `config/operator-production.json`

### 2026-07-05 — Phase A–D parity closure

- **Phase A–D** parity closure complete: 19 verified v1, 0 partially verified.
  Gates: `npm run verify:phase-a` … `npm run verify:phase-d`.
  Snapshot and ledger updated; `next_slice=complete` in
  `config/parity-closure-order.json`.
- Governance docs amended: `docs/CUTOVER_DECISION.md`,
  `docs/FINAL_PARITY_VERIFICATION.md` (this append log).
- Full axon-local retirement still **not approved** — operator sign-off on
  production switch from `:7734` to `:4173` remains the sole blocker.

### 2026-07-05 (continued)

- **TEST-10** final parity verification and cutover decision: 7 verified v1,
  12 partially verified; bounded cutover approved; axon-local retirement not
  approved. Gate: `./scripts/verify/test10-final-parity-cutover.sh`.

- **TEST-9** cross-repo planning migration verified: canonical bundle in
  `docs/planning/`, manifest validation, cutover references updated.
  Gate: `./scripts/verify/test9-cross-repo-planning-migration.sh`.

- **TEST-8** dedicated-server readiness verified: deployment topology, env
  validation, systemd/Caddy/compose artifacts, readiness `state_dir`/`mode`.
  Gate: `./scripts/verify/test8-dedicated-server-readiness.sh`.

- **TEST-7** operator presence slice verified: `operator_presence` on briefing,
  spoken-alert policy, persona voice line, mobile compact shell.
  Gate: `./scripts/verify/test7-operator-presence.sh`.

- **TEST-6** KAIRO watch rules slice verified: `watch_rule` metadata on inbox
  items, observe/advise/approval/execute mapping, Attention mode chip.
  Gate: `./scripts/verify/test6-kairo-watch-rules.sh`.

- **TEST-5** delivery receipts slice verified: severity routing, receipt store,
  inbox `delivery_state`, control-plane `/api/delivery/receipts`, Attention
  sidebar delivery badge. Gate: `./scripts/verify/test5-delivery-receipts.sh`.

### 2026-07-05

- Locked initial cutover order.
- Baseline assessment: usable for bounded local development, not yet a
  replacement for `axon-local` continuous multi-project development.
