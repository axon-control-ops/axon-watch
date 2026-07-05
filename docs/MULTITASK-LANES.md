# Axon-X Post-Stabilization Multi-Agent Lanes

This map defines non-overlapping ownership after the stabilization pass.
Use it before resuming parallel agent work.

## Serial-Only Truth (Coordinator Lane)

One lane owns semantic truth. No other lane may edit these without coordinator
approval:

- `axon-local/Plans/Axon-Watch/run-state.md`
- `packages/shared-types/src/run.ts`
- `packages/shared-types/src/runtime.ts`
- `packages/shared-types/src/briefing.ts`
- `packages/shared-types/src/signals.ts`
- `services/control-plane/app/domain/run_state.py`
- `services/control-plane/app/domain/run_transitions.py`
- `docs/contracts/run-state-stop-resume-amendment-request.md`

Coordinator responsibilities:

- approve or reject planning amendments
- resolve contract drift before merge
- assign slices with explicit file ownership
- block parallel edits that touch the same truth surface

## Safe Parallel Lanes

### Lane A — Watch Depth

Ownership:

- `services/axon-watch/app/signals/*`
- `services/axon-watch/app/main.py` (watch routes only)
- watch-specific tests under `tests/test_watch_*`

May:

- add signal producers and ranking metadata
- extend watch inbox payloads additively

Must not:

- change run-state semantics
- change shared DTO fields without coordinator approval

### Lane B — Console Shell Surfaces

Ownership:

- `apps/console-web/src/**`
- console-web styles and partial shell layout

**Layout lock:** region geometry and dock seam order are frozen — see
`docs/UI_LAYOUT_LOCK.md` and ADR-004 through ADR-007. Lane B may polish and bind
DTOs inside regions but must not rearrange the shell without coordinator approval
and a new ADR.

May:

- build editor, terminal, preview, and dock surfaces
- consume existing control-plane APIs

Must not:

- invent run phases or approval semantics locally
- add briefing mutation controls inside the display-only briefing panel

### Lane C — Control-Plane Product Behavior

Ownership:

- `services/control-plane/app/runs/*`
- `services/control-plane/app/persistence/*`
- `services/control-plane/app/main.py` (run/briefing routes)
- control-plane tests

May:

- deepen stop/resume/review flows within frozen transitions
- extend SQLite persistence and history receipts

Must not:

- bypass approval boundary through generic resume
- add transitions without contract amendment

### Lane D — Dev Runtime And Verification

Ownership:

- `scripts/dev/**`
- root `package.json` verify scripts
- `docs/HOW-TO-HANDBOOK.md`
- `README.md`

May:

- improve startup supervision, health probes, and verify entrypoints

Must not:

- change product semantics while touching tooling

## Blocked Until Explicit Assignment

Do not start these until coordinator opens the slice:

| Item | Owner | Reason |
|---|---|---|
| KAIRO operator-presence integration (JX-1–JX-5) | Coordinator | Cross-cutting persona, voice, watch rules — planning only in `axon-local` |
| Cross-repo planning migration | Coordinator | `axon-local/Plans/Axon-Watch/` remains frozen planning home |
| Shared-contract field changes | Coordinator | `packages/shared-types`, run-state truth surfaces |

## Completed Queue

Work landed on `dev` (verified 2026-07-04):

| ID | Lane | Slice | Commit area |
|---|---|---|---|
| B1 | C (+ B) | Chat orchestration hook → superseded by C2 | `chat/orchestration.py` |
| B2 | B | Workspace catalog policy (doc) | `docs/WORKSPACE_CATALOG.md` |
| A1 | A | Bootstrap degraded signal clarity | watch summary copy |
| C1 | C (+ B) | Run history receipts in Active Run dock | `GET /api/runs/{id}/history` |
| D1 | D | Dev verify evidence + nightly gate | `npm run verify:evidence` |
| **D2** | D | Shell boot + latency timing evidence | `measure_shell_boot.py`, `collect-verify-evidence.sh` |
| UX-4 | B | SSE live refresh + interruptive signals | `GET /api/live/events` |
| C2 | C (+ B) | Bounded command executor | `command_executor.py` |
| C3 | C (+ B) | Briefing **Notice/Advise** projection | `operator_briefing_rhythm.py` |
| C4 | C (+ B) | Attention sidebar **approve/reject** wired to run API | `AttentionStackPanel.vue` |
| C5 | C (+ B) | Command executor **git status** + **resume from review** | `command_executor.py`, chat orchestration |
| B3 | B | Compact operator responsive CSS | `mockup-shell.css` `@media` |
| ADR-005 | B | Operator sidebar **Attention** toggle | `LeftSidebar`, `AttentionStackPanel` |
| ADR-006 | B | Command hero autosize + footer KAIRO CTA | `CommandSeamPanel`, `StatusBar` |
| ADR-007 p1 | B | Hide Monaco in Operator; IDE terminal collapse | `CenterWorkbench.vue` |
| **B7** | B | **Operator status/radar panel** (ADR-007 phase 2 option A) | `OperatorStatusRadarPanel.vue` |
| **ADR-007 p3** | B | **Mission control v1 + Operator terminal collapse parity** | `OperatorStatusRadarPanel.vue`, `CenterWorkbench.vue`, `docs/OPERATOR_MISSION_CONTROL_V1.md` |

## Active Queue (resume here)

One slice per pass; run the verification gate before the next item.

| Priority | ID | Lane | Slice | Status |
|---|---|---|---|---|
| **1** | **TEST-0** | All | Manual acceptance on `workspace_smoke`: Command executor, KAIRO Notice/Advise, Attention sidebar, mission control v1, compact layout | **Done** — `./scripts/verify/test0-workspace-smoke.sh` + `tests/test_test0_workspace_smoke_acceptance.py` (2026-07-05) |
| **2** | **TEST-1** | C (+ D) | Real project/workspace connection — bindings file, catalog enrichment, terminal/command cwd bridge, live `git status` in `workspace_axon_local` | **Done** — `./scripts/verify/test1-workspace-project-connection.sh` + `docs/WORKSPACE_PROJECT_CONNECTION.md` (2026-07-05) |
| **3** | **TEST-2** | C | Workspace handoff slice — persisted cross-workspace record + target workspace summary | **Done** — `./scripts/verify/test2-workspace-handoff.sh` + `docs/WORKSPACE_HANDOFF.md` (2026-07-05) |
| **4** | **TEST-3** | A (+ C) | Watch connectors — HTTP probe config, watch summary/connectors, runtime projection, required-failure signals | **Done** — `./scripts/verify/test3-watch-connectors.sh` + `docs/WATCH_CONNECTORS.md` (2026-07-05) |
| **5** | **TEST-4** | A (+ C) | Watch command/event/status depth — reprobe + refresh commands, events log, summary observation, CP proxy | **Done** — `./scripts/verify/test4-watch-command-event-depth.sh` + `docs/WATCH_COMMAND_EVENT_DEPTH.md` (2026-07-05) |
| **6** | **TEST-5** | A (+ C) | Delivery receipts — severity routing, receipt store, inbox delivery_state, CP proxy, Attention badge | **Done** — `./scripts/verify/test5-delivery-receipts.sh` + `docs/DELIVERY_RECEIPTS.md` (2026-07-05) |
| **7** | **TEST-6** | A (+ C) | KAIRO watch rules — `watch_rule` on inbox items, mode mapping, Attention chip | **Done** — `./scripts/verify/test6-kairo-watch-rules.sh` + `docs/KAIRO_WATCH_RULES.md` (2026-07-05) |
| **8** | **TEST-7** | B (+ C) | Operator presence — persona, spoken-alert eligibility, mobile compact shell | **Done** — `./scripts/verify/test7-operator-presence.sh` + `docs/OPERATOR_PRESENCE.md` (2026-07-05) |
| **9** | **TEST-8** | D | Dedicated-server readiness — topology, env validation, systemd/Caddy/compose | **Done** — `./scripts/verify/test8-dedicated-server-readiness.sh` + `docs/DEDICATED_SERVER_READINESS.md` (2026-07-05) |
| 4 | C4 | C (+ B) | Wire **approve/reject** actions from Attention sidebar to existing API | **Done** — `AttentionStackPanel` APPROVE/REJECT → `/api/runs/{id}/approve|reject` |
| 5 | C5 | C (+ B) | Expand command executor (`git status`, resume-from-review command) | **Done** — `git status` + `resume from review` via chat orchestration |
| 6 | D2 | D | Capture `shell_boot_readiness` + latency timing evidence | **Done** — `measure_shell_boot.py` + `collect-verify-evidence.sh` |

## Blocked / Coordinator-only

| ID | Lane | Slice |
|---|---|---|
| JX-1–5 | Coordinator | KAIRO watch rules, delivery policy, voice, persona, mobile |
| — | Coordinator | Cross-repo planning migration |
| — | Coordinator | `axon-local` ADR-005 (KAIRO presence layer) — **not** the same as repo ADR-005 (sidebar attention) |

## Layout ADR index (implementation repo)

| ADR | Topic |
|---|---|
| ADR-004 | Five-region shell grid (locked geometry) |
| ADR-005 | Operator sidebar Workspaces \| Attention toggle |
| ADR-006 | Command/KAIRO hero autosize + footer briefing CTA |
| ADR-007 | Operator workbench demotion — phase 1 editor hide, **phase 2/3 mission control v1**, terminal parity — see [`OPERATOR_MISSION_CONTROL_V1.md`](OPERATOR_MISSION_CONTROL_V1.md) |

## Recently Landed (detail)

- approval thin slice (`requires_approval`, approve/reject)
- review-ready entry, completion, and resume-from-review
- workspace list API and DTO-bound Monaco hosts
- backend PTY terminal attachment (WebSocket, workspace-scoped)
- **zsh PTY via `ZDOTDIR`**
- file-backed Monaco editing + nested workspace explorer
- split mockup shell regions + resizable bottom terminal dock
- workspace-scoped chat thread rehydration
- **chat command dispatch** attach vs new run
- **bounded command executor (C2)** — health/list/read + execution receipts
- **command executor (C5)** — `git status` in workspace root; `resume from review` resumes primary `review_ready` run
- **briefing Notice/Advise (C3)** — canonical rhythm strings
- **SSE live refresh (UX-4)**
- **verify evidence tooling (D1)**
- **Operator layout (ADR-005/006)** — conversation-first right dock, Attention sidebar
- **Workbench demotion (ADR-007 p1)** — editor hidden in Operator
- **Operator status/radar panel (B7 / ADR-007 p2)** — fills upper workbench void with DTO-backed metrics + radar
- **ADR-007 p3** — mission control v1 (execution stage, live feed, run controls, mode-specific terminal defaults); spec: `docs/OPERATOR_MISSION_CONTROL_V1.md`
- **TEST-0** — `workspace_smoke` acceptance gate: `./scripts/verify/test0-workspace-smoke.sh` + `tests/test_test0_workspace_smoke_acceptance.py` (2026-07-05)
- **TEST-1** — real project/workspace connection: bindings → terminal/Monaco/command cwd; `./scripts/verify/test1-workspace-project-connection.sh` + `docs/WORKSPACE_PROJECT_CONNECTION.md` (2026-07-05)
- **TEST-2** — workspace handoff slice: `POST/GET /api/workspaces/{id}/handoffs` + target summary; `./scripts/verify/test2-workspace-handoff.sh` + `docs/WORKSPACE_HANDOFF.md` (2026-07-05)
- **TEST-3** — watch connectors: HTTP probes + `/api/connectors` + runtime summary projection; `./scripts/verify/test3-watch-connectors.sh` + `docs/WATCH_CONNECTORS.md` (2026-07-05)
- **TEST-4** — watch command/event depth: `/api/watch/commands`, events log, summary `observation`; `./scripts/verify/test4-watch-command-event-depth.sh` + `docs/WATCH_COMMAND_EVENT_DEPTH.md` (2026-07-05)
- **TEST-5** — delivery receipts: `/api/delivery/receipts`, inbox `delivery_state`, Attention badge; `./scripts/verify/test5-delivery-receipts.sh` + `docs/DELIVERY_RECEIPTS.md` (2026-07-05)
- **TEST-6** — KAIRO watch rules: inbox `watch_rule`, mode chip; `./scripts/verify/test6-kairo-watch-rules.sh` + `docs/KAIRO_WATCH_RULES.md` (2026-07-05)
- **TEST-7** — operator presence: briefing `operator_presence`, spoken-alert policy, mobile compact; `./scripts/verify/test7-operator-presence.sh` + `docs/OPERATOR_PRESENCE.md` (2026-07-05)
- **TEST-8** — dedicated-server readiness: topology + systemd/Caddy/compose + validate script; `./scripts/verify/test8-dedicated-server-readiness.sh` + `docs/DEDICATED_SERVER_READINESS.md` (2026-07-05)

## Assignment Rules

1. One slice, one lane, one verification gate.
2. No two agents edit the same file in the same pass.
3. Shared-contract changes require coordinator review before coding starts.
4. Every slice ends with:

```bash
npm run verify
python3 -m unittest discover -s tests
./scripts/dev/check-health.sh
```
