# Axon-Watch Parity Ledger

## Purpose

This ledger tracks the must-keep behaviors that the new `axon-watch` product
 must preserve from current Axon.

It is the canonical parity checklist used during migration and delivery.

## Ledger Rule

Each must-keep behavior needs:

- current source surface
- new owner
- migration slice
- verification method
- acceptable temporary degradation, if any

Parity is complete only when the new owner is verified, not when the behavior is
 merely discussed in planning.

## Must-Keep Behaviors

| Behavior | Current source surface | New owner | Migration slice | Verification method | Acceptable temporary degradation |
|---|---|---|---|---|---|
| Run stop / resume | Current control-plane run surfaces, transcript controls, operator controls in `axon-local` | `control-plane` run-state layer + `console-web` action surfaces | Run-state thin slice | End-to-end run flow with stop and resume receipts; UI verifies same state in dock and runtime strip | Short-term: resume available only from primary run view, as long as canonical state remains correct |
| Approval boundaries | Existing Axon guarded actions and approval-required flows | `control-plane` approval system | Approval thin slice | Contract test on approval phase + UI proof that approval blocks execution everywhere consistently | Short-term: reduced approval presentation polish, but no loss of explicit boundary |
| Review-ready state | Existing review/apply/discard and follow-up decision surfaces | `control-plane` run-state + review layer | Approval and review slice | Canonical `review_ready` transition + UI review state visible in dock and run summary | Short-term: fewer review affordances, but explicit review-ready phase must exist |
| Workspace handoffs | Existing workspace handoff flows in Axon | `control-plane` workspace orchestration | Workspace/handoff slice | One cross-workspace handoff from request to target workspace summary | Short-term: manual follow-through allowed if explicit handoff record exists |
| Real project/workspace connection | Current Axon project roots and multi-repo dev layout | `control-plane` workspace bindings + catalog + terminal/file/command roots | TEST-1 workspace project connection slice | Bindings config + `/api/workspaces` enrichment + live `git status` in bound `workspace_axon_local` | Short-term: manual bindings file acceptable; missing allowlist safety is not |
| Operator vs IDE mode semantics | Current Axon operator/IDE planning direction and mode semantics | `console-web` layout and shared state model | UI shell and layout-mode slice (ADR-005/006/007) | Visual + store verification: Operator = Attention sidebar, conversation-first dock, **mission control v1** in center (execution stage + live feed + run controls), editor hidden, **terminal dock collapsed by default** (mode-specific session key); IDE = explorer + full editor + collapsible center terminal + agent dock | Short-term: v1 feed is receipt-depth only; semantic divergence is not |
| Dock behavior | Current agent dock behavior and compact thread/dock ergonomics | `console-web/rightDock` + center bottom dock | Agent dock slice (ADR-005/006/007) | UI verification: Operator right dock = Conversation + Command/KAIRO hero; ops seams in left Attention; center terminal reopen via mission-control chip + dock strip; IDE center terminal close/show via status bar | Short-term: reduced visual richness acceptable; duplicated run semantics are not |
| Runtime summary behavior | Current runtime summary / runtime truth expectations | `control-plane` runtime summary assembler | Runtime summary slice | DTO contract tests + boot-path UI render using summary only | Short-term: fewer fields acceptable if boot-critical identity and degraded state remain correct |
| Initial shell boot expectations | Current console boot-order lessons from Axon | `console-web` boot flow + `control-plane` bootstrap APIs | Shell boot slice | Measured boot checklist: settings/workspaces/runtime summary/shell render order | Short-term: some deferred panels may remain empty after first paint, but shell must render cleanly |
| Signal / inbox consistency | Current attention / proactive / signal behavior concepts | `axon-watch` signal layer + `control-plane` inbox projection | First watch signal slice + ranking slice | One signal rendered consistently across inbox, summary, and detail surfaces | Short-term: fewer signal types acceptable; inconsistent severity/status is not |
| Desktop and browser startup expectations | Current browser and desktop startup expectations in Axon | `console-web` shell + deployment/bootstrap layer | Repo bootstrap + deployment slice | Verified browser startup and documented desktop startup contract | Short-term: desktop packaging may lag, but startup expectations must be documented and browser flow stable |
| KAIRO watch rules | `proactive_next_actions.watch_rule_for_item()` and interruption explanation in `operator_notification_policy.py` | `axon-watch` signal ranking + delivery policy inputs | JX-1 watch-rule metadata slice | Contract test that `observe` / `advise` / `approval` / `execute` map consistently from signal payload to interruption policy | Short-term: fewer auto-generated reasons acceptable; mode semantics must not drift |
| Spoken high-value alerts | `voice-attention-monitor.js`, `voice-playback.js`, JARVIS toggle in `voice-conversation.js` | `console-web` voice layer + control-plane briefing API | JX-4 operator presence slice | End-to-end proof: high-severity signal becomes spoken alert only when privacy and presence settings allow | Short-term: desktop-first spoken alerts acceptable; mobile may remain push-first |
| Delivery receipts for operator attention | JR-002 delivery status/receipt patterns, `operator_notification_policy.py` | `axon-watch/delivery` + control-plane inbox projection | JX-2 delivery policy slice | Contract test on delivery attempt/receipt events plus UI proof of receipt visibility | Short-term: fewer channels acceptable; missing receipts for critical signals is not |
| Executive operator rhythm | `executive_operator_workflow.py`, JARVIS readiness plan operator loop | `control-plane` briefing + run orchestration | JX-3 briefing projection slice | Briefing API returns Notice/Advise/Decide/Execute/Verify/Report shaped summary from canonical state | Short-term: fewer narrative fields acceptable; missing approval/execute boundaries is not |
| KAIRO persona and operator copy | `jarvis_personality.py`, `jarvis_mode` settings, companion voice context | `packages/prompt-contracts` + presentation layer | JX-5 persona contract slice | Contract test on persona module output; UI/voice proof that tone changes do not alter run/signal truth | Short-term: reduced voice identity options acceptable |
| Mobile operator cockpit compactness | `mobile-voice-jarvis-controller.js`, JR-001 mobile cockpit direction | `console-web/features/operator-presence` | JX-4 mobile presence slice | Responsive UI proof on compact operator surfaces using real briefing/signal DTOs | Short-term: foreground mobile monitoring only; no false background-listening claim |

## Parity States

Suggested status vocabulary for future use:

- `planned`
- `in_progress`
- `partially_verified`
- `verified`
- `superseded`

## Current Verification Snapshot (2026-07-05)

Implementation repo: `axon-watch` on branch `dev`. This table records **observed**
status against the must-keep behaviors above — not aspirational completion.

| Behavior | Status | Evidence |
|---|---|---|
| Run stop / resume | `partially_verified` | API + dock actions; not full E2E receipt audit |
| Approval boundaries | `partially_verified` | Approve/reject endpoints + dock seam |
| Review-ready state | `partially_verified` | `review_ready` phase visible in dock + status bar |
| Operator vs IDE mode semantics | `partially_verified` | ADR-007 v1 + **TEST-0 pass** (2026-07-05): `test_test0_workspace_smoke_acceptance.py`, mission control unit tests, live git status / resume-from-review on `workspace_smoke` |
| Real project/workspace connection | `partially_verified` | **TEST-1 pass** (2026-07-05): `workspace_project_bindings.py`, `test_test1_workspace_project_connection_acceptance.py`, live `git status` in bound `workspace_axon_local` |
| Workspace handoffs | `partially_verified` | **TEST-2 pass** (2026-07-05): `POST/GET /api/workspaces/{id}/handoffs`, persisted record + target workspace summary in `test_test2_workspace_handoff_acceptance.py` |
| Watch connectors / runtime awareness | `partially_verified` | **TEST-3 pass** (2026-07-05): `config/watch-connectors.json`, `/internal/watch/connectors`, `/api/connectors`, runtime summary `connectors` block |
| Watch command / event / status depth | `partially_verified` | **TEST-4 pass** (2026-07-05): `reprobe_connector`, `/api/watch/events`, summary `observation`, `test_test4_watch_command_event_acceptance.py` |
| Delivery receipts for operator attention | `partially_verified` | **TEST-5 pass** (2026-07-05): `app/delivery/`, `/api/delivery/receipts`, inbox `delivery_state`, Attention sidebar badge |
| Dock behavior | `partially_verified` | Operator terminal collapse + reopen (chip/strip/✕); IDE status-bar TERMINAL restore; run controls in center + Attention sidebar |
| Runtime summary behavior | `partially_verified` | Boot path uses `/api/runtime/summary`; Phase 4 API E2E in `test_control_plane_skeleton_e2e.py` |
| Initial shell boot expectations | `partially_verified` | Sequential bootstrap; timing fitness PENDING |
| Signal / inbox consistency | `partially_verified` | Phase 5 CP→watch E2E in `test_control_plane_watch_integration.py`; bootstrap signals in dev |
| Desktop and browser startup | `partially_verified` | `./scripts/dev/up.sh` documented and verified |
| KAIRO watch rules | `partially_verified` | **TEST-6 pass** (2026-07-05): `watch_rule` on inbox items, observe/advise/approval/execute mapping, Attention mode chip |
| Spoken high-value alerts | `partially_verified` | **TEST-7 pass** (2026-07-05): spoken-alert eligibility on briefing, browser speech hook with session dedupe |
| Executive operator rhythm | `partially_verified` | Briefing API consumed; narrative fields thin |
| KAIRO persona and operator copy | `partially_verified` | **TEST-7 pass** (2026-07-05): `persona_voice_line` on `/api/briefing`, BriefingPanel consumption |
| Mobile operator cockpit compactness | `partially_verified` | **TEST-7 pass** (2026-07-05): `viewport_compact` + `console-shell--mobile-compact`, `foreground_only: true` |

## Verification Rule

Parity verification should prefer:

1. contract proof
2. focused end-to-end proof
3. visible UI proof for user-facing behavior

Do not mark parity complete from documentation alone.

## Acceptance Criteria

This ledger is being followed when:

- each must-keep behavior has a documented new owner
- migration slices are explicit
- temporary degradation is intentional and bounded
- parity is tracked as verified behavior rather than aspiration
