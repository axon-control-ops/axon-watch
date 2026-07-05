# Axon-Watch Implementation Roadmap

## Purpose

This document defines the staged implementation order for the new
`/home/edp/axon-nvme/repos/axon-watch` repo.

It is the execution roadmap that translates the product, architecture, UI, and
contract docs into a build sequence.

## Roadmap Rule

Build in slices that preserve clarity:

1. source of truth first
2. skeletons before complexity
3. explicit contracts before integrations
4. end-to-end thin slices before broad feature expansion

## Phase 0 — Planning Lock

Goal:

- finish the first complete planning bundle before scaffolding the repo

Deliverables:

- `PRODUCT.md`
- `ARCHITECTURE.md`
- `UI_SPEC.md`
- run-state, signal, watch API, control API, and runtime summary contracts
- core ADRs

Exit criteria:

- service boundaries are explicit
- UI shell rules are explicit
- execution truth is explicit

## Phase 1 — Repo Bootstrap

Goal:

- create the new repo with the agreed folder structure and base toolchain

Deliverables:

- repo root
- frontend app shell
- `control-plane` service shell
- `axon-watch` service shell
- shared packages area
- docs, scripts, and infra skeletons

Exit criteria:

- the repo installs and starts in a minimal development mode
- empty services have health endpoints
- the frontend shell renders

## Phase 2 — Shared Contracts And Types

Goal:

- implement the typed shared DTO layer before deep feature work

Deliverables:

- shared type definitions for runs, signals, inbox items, runtime summary
- contract version strategy
- frontend-consumable generated or hand-maintained shared types

Exit criteria:

- backend and frontend can compile against the same core DTO vocabulary

## Phase 3 — UI Shell

Goal:

- build the integrated shell without deep feature logic first

Deliverables:

- UX-0 JARVIS-forward tokens, boot/wake sequence, and shell hierarchy
- UX-1 runtime-backed topbar and status bar
- UX-2 right dock seams with operator-facing titles
- UX-3 KAIRO presence layer with briefing hero in Operator mode
- UX-4 live update polish
- left sidebar, center workbench (with embedded terminal dock), and right dock region hosts
- operator / IDE layout switching

See [`UI_COMPOSITION_SPEC.md`](UI_COMPOSITION_SPEC.md) and
[`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md) for region composition, visual
north star, DTO bindings, and slice exit criteria.

Exit criteria:

- the shell renders cleanly from `RuntimeSummary` with JARVIS-forward chrome
- topbar, status bar, and dock show the same truth
- Operator mode presents KAIRO briefing as the default visual hero
- layout modes switch without contract changes
- dev seam labels are hidden outside explicit dev diagnostics mode
- the UI can host editor, terminal, dock, and signals without branching into separate apps

## Phase 4 — Control-Plane Skeleton

Goal:

- stand up the interactive backend with canonical run-state handling

Deliverables:

- health/readiness
- runtime summary
- run creation/list/detail endpoints
- stop/resume/approval endpoint stubs
- workspace list endpoints

Exit criteria:

- the UI can render runtime summary and a fake or minimal run list from real APIs

## Phase 5 — Watch Skeleton

Goal:

- stand up the watcher process and internal API shape

Deliverables:

- health/readiness
- summary endpoint
- inbox endpoint
- signals endpoint
- event stream stub
- command endpoint stub

Exit criteria:

- the control plane can call the watch service through the documented contract

## Phase 6 — First End-To-End Thin Slice

Goal:

- connect one real watcher-produced signal to one real UI surface

Suggested slice:

- one watch health signal
- one inbox item
- one runtime summary update
- one UI card / strip / inbox row

Exit criteria:

- one real event is produced, persisted, exposed, and rendered end to end

## Phase 7 — Canonical Run Flow

Goal:

- connect one real run lifecycle through the new run-state model

Suggested slice:

- create run
- enter `starting`
- enter `executing`
- pause or await approval
- resume
- complete

Exit criteria:

- one run can move through canonical phases with persisted receipts

## Phase 8 — IDE Surfaces

Goal:

- add real editor/terminal/dock behavior on top of the shell

Deliverables:

- Monaco integration
- xterm integration
- dock summary tied to real run DTOs
- workspace navigation

Exit criteria:

- one hands-on coding workflow is possible in the new shell

## Phase 9 — Signal And Approval Depth

Goal:

- expand the control-plane strength that makes the product distinct

Deliverables:

- approval queue
- review-ready state
- richer inbox ranking
- delivery receipts
- cross-workspace signals

Exit criteria:

- the product feels like an actual control plane, not only a code shell

## Phase 9B — KAIRO Operator Presence

Goal:

- integrate `KAIRO` as a composed operator-presence layer without creating a
  new monolith

Suggested slices:

- JX-1 watch-rule metadata in canonical signals
- JX-2 delivery policy and receipts in Watch
- JX-3 operator briefing projection in control plane
- JX-4 Vue operator presence shell and spoken-alert hooks
- JX-5 persona and spoken-alert contracts

Deliverables:

- `watch_rule` on signal events
- delivery receipts for watch-born events
- briefing API for deck/voice/mobile cockpit
- operator-presence settings preset (replacement for the old JARVIS toggle)
- persona module in `packages/prompt-contracts`

Exit criteria:

- one high-severity signal can move from Watch -> briefing -> optional spoken alert with receipts
- persona changes do not alter run-state or signal truth
- mobile scope remains honest: foreground + push, not false background listening

See [`KAIRO_MODE.md`](KAIRO_MODE.md) and
[`ADR-005-kairo-as-operator-presence-layer.md`](ADR-005-kairo-as-operator-presence-layer.md).

## Phase 10 — Import And Adapt

Goal:

- bring in proven concepts from `axon-local` deliberately

Rules:

- only import from the `IMPORT_MATRIX.md`
- every copied behavior gets a new bounded owner
- no wholesale UI or scheduler inheritance

Exit criteria:

- reused capabilities are mapped cleanly into the new architecture

## Phase 11 — Dedicated Server Readiness

Goal:

- verify that the design already works in the long-term target topology

Deliverables:

- process supervision spec
- reverse proxy / TLS plan
- config externalization
- health and readiness checks across services

Exit criteria:

- the product can move to a dedicated server without redesigning the boundaries

## Ongoing Rules

At every phase:

- preserve one source of truth
- preserve typed shared contracts
- preserve explicit run-state truth
- preserve the watch/control split
- prefer thin slices over broad rewrites

## Acceptance Criteria

The roadmap is being followed when:

- the repo grows by bounded slices
- every major feature lands against an existing contract
- the first real end-to-end flows arrive before broad feature sprawl

## Implementation Status (2026-07-04)

Verified in `/home/edp/axon-nvme/repos/axon-watch` (`dev` branch). Gates:
`npm run verify` (104 Python + 75 Vitest), manual operator acceptance on
`workspace_smoke`.

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Planning lock | **complete** | This bundle + ADR-005 KAIRO presence |
| Phase 1 — Repo bootstrap | **complete** | Three-service dev stack on 4173/8787/8788 |
| Phase 2 — Shared contracts | **partial** | Core DTOs + fixtures; not all contracts migrated |
| Phase 3 — UI shell | **partial** | UX-0–UX-2 largely landed; UX-3/UX-4 incomplete |
| Phase 4 — Control-plane skeleton | **verified (API E2E)** | Runs/workspaces/runtime summary proven via `test_control_plane_skeleton_e2e.py` against live watch |
| Phase 5 — Watch skeleton | **verified (contract E2E)** | CP→watch health/inbox/summary projection via `test_control_plane_watch_integration.py`; summary/events/command stubs still deferred |
| Phase 6 — First E2E thin slice | **partial** | Bootstrap signals render in dock; watch degraded in dev |
| Phase 7 — Canonical run flow | **partial** | review_ready + stop/resume paths tested |
| Phase 8 — IDE surfaces | **partial** | Monaco file tree, PTY terminal (zsh ZDOTDIR fix), scrollback |

**Recent verified slices (Lane B / control-plane):**

- Locked five-region shell + ADR-004 layout (`RightDock`, `DockHeroPanel`, etc.)
- Operator seam titles (`Active Run`, `Approvals`, `Signals`, `Conversation`, `Command`)
- Chat command dispatch attach vs new run (`chat/dispatch.py` + frontend `refreshRunSurfaces`)
- Silent empty workspace thread lookup (HTTP 200, `thread_id: null`)
- Bootstrap workspace catalog trim (`mergeMockupWorkspaceCatalog`, `workspace_smoke` default)
- Interactive PTY terminal with workspace-scoped zsh via `ZDOTDIR` (not `--rcfile`)

**Not started / blocked:**

- KAIRO operator-presence integration (ADR-005) — coordinator assignment required
- Real chat/agent orchestration beyond system ack stub
- Fitness timing gates (`shell_boot_readiness`, latency budgets) — still PENDING
- Remote deployment / dedicated-server phase
