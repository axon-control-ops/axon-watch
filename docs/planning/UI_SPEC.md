# Axon-Watch UI Spec

## Goal

Create one integrated shell that combines:

- VS Code-style editor and workbench geometry
- Cursor-style agent workflow and dock behavior
- Axon-style control-plane awareness, signals, approvals, and workspace oversight

This must feel like one product, not a browser admin panel plus a separate IDE.

## Core Layout Model

The shell should support two primary layout modes:

1. `operator`
2. `ide`

Both modes must use:

- the same backend contracts
- the same run-state truth
- the same signal model
- the same action semantics

Only placement, density, and emphasis should change between modes.

## Shared Regions

The UI is composed from these stable regions (locked 2026-07-04 — see
`axon-watch/docs/UI_LAYOUT_LOCK.md`):

- `topbar`
- `leftSidebar`
- `centerWorkbench` (includes embedded terminal dock)
- `rightDock`
- `statusBar`

The terminal is **not** a separate top-level shell row; it lives inside
`centerWorkbench`.

## Operator Mode

Operator mode is for:

- monitoring multiple workspaces
- reading signals and attention items
- reviewing approvals
- steering active runs
- checking handoffs and summaries

Emphasis:

- signal and run truth first
- transcript and coordination first
- coding surfaces visible but secondary

## IDE Mode

IDE mode is for:

- active coding
- reviewing diffs
- using terminal and browser preview
- working with the agent dock alongside the editor

Emphasis:

- editor first
- terminal and preview nearby
- agent dock always present
- operator truth still visible without taking over the layout

## Primary Surfaces

### Explorer

Shows project/workspace structure and editor navigation.

### Editor

Monaco-backed code editor with tabs, diff review, and breadcrumb support.

### Terminal

xterm.js-backed terminal surface for guarded shell access.

### Browser / Preview

Embedded preview/debug surface for web-facing work.

### Agent Dock

Compact thread, composer, status, stop/resume, and next actions in a dedicated dock.

### Signals / Inbox

Unified signal surface for runtime issues, connector alerts, approvals, and watch notifications.

## Interaction Rules

1. There must be one composer model across the whole app.
2. There must be one stop/resume/approval action model across the whole app.
3. There must be one meaning for run phases across all surfaces.
4. Operator status text must come from one canonical run-presentation layer.
5. Signal severity and routing must stay consistent across dashboard, dock, and mobile-friendly views later.

## UI State Rules

Global UI state should include:

- current workspace
- current layout mode
- active run summary
- signal counts and ranked inbox
- active editor tabs
- active terminal session
- active dock/thread context

State should be explicit and centralized, not inferred ad hoc from DOM fragments.

## Technology Direction

Recommended stack:

- Vue 3
- TypeScript
- Pinia
- Monaco Editor
- xterm.js

Reason:

- component boundaries for a large application
- predictable shared state
- better fit for an IDE-grade interface than progressive Alpine enhancement

## Non-Negotiables

1. No mixed ownership of the shell.
2. No duplicate composer logic.
3. No duplicate run-state logic.
4. No second-class operator view hidden behind IDE-only assumptions.
5. No IDE-only rewrite that drops Axon’s control-plane strengths.

## Visual Direction

AXON-X uses a **JARVIS-forward** presentation layer on top of Cursor/VS Code
workbench mechanics.

Canonical spec:

- [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md)

Desired feeling:

- cinematic but controlled
- premium and high-trust
- always-on and aware
- operator-grade under pressure
- code-capable in IDE mode

Avoid:

- generic admin dashboard styling
- unreadable neon on every surface
- movie prop theatrics that hide run/signal truth

## Reference Archetypes

AXON-X should draw from three reference families:

1. JARVIS-style cinematic presence
2. SOC / command-center operational density
3. IDE-grade workbench clarity

These references are documented in
[`UI_REFERENCE_ARCHETYPES.md`](UI_REFERENCE_ARCHETYPES.md).

Decision rule:

- JARVIS-forward shell chrome is the default presentation language
- borrow operational hierarchy from command centers
- keep workbench ergonomics grounded in real IDE usage

Full token, HUD, boot, and copy rules live in
[`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md).

## Command-Center UX Rules

1. Every major screen must support a three-step scan: global state, active
   exception, then evidence/action.
2. There must be one visual hero at a time: the active run, approval, signal,
   diff, or editor task.
3. KAIRO briefing is the default visual hero in Operator mode.
4. Motion must communicate state changes, not act as ambient decoration.
5. Glass, glow, and HUD corner treatment are part of the default shell chrome.
6. Dense information is acceptable only when hierarchy remains readable in long
   sessions.
7. Operator mode should feel like a JARVIS command deck; IDE mode should feel
   like a premium coding environment; both must preserve the same truth.

## KAIRO Presence Primitives

The UI should support a bounded set of KAIRO presence primitives:

- topbar presence chip
- dock voice / attention status
- concise briefing card
- optional compact pulse/orb indicator
- spoken-alert status strip

These are presentation affordances over canonical DTOs, not separate truth
systems.

Detailed region composition, DTO bindings, and delivery slices are defined in
[`UI_COMPOSITION_SPEC.md`](UI_COMPOSITION_SPEC.md).

## Visual System Rules

Use the token system in [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md).

Summary:

- very dark atmospheric base surfaces
- glass panels with cyan HUD borders
- semantic color reserved for severity and run-state meaning
- KAIRO cyan accent for identity and presence
- strong contrast for low-light and long-session use

Avoid:

- rainbow or holographic treatment on every panel
- fake telemetry decoration without real data
- always-spinning cinematic elements in normal workflows
- semantic colors being reused as brand chrome
- dev seam labels in operator-facing surfaces

## Initial UI Delivery Order

Follow [`UI_COMPOSITION_SPEC.md`](UI_COMPOSITION_SPEC.md) slices:

1. UX-0 — design tokens and shell hierarchy
2. UX-1 — runtime-backed topbar and status bar
3. UX-2 — right dock seams
4. UX-3 — KAIRO presence layer
5. UX-4 — live update polish
6. Explorer + editor shell
7. Terminal + preview shell
8. Full signal/inbox surface beyond dock summary

## Acceptance Criteria

The UI spec is being honored when:

- the shell can support both operator and IDE workflows without branching into separate products
- the user can code, monitor, approve, and steer from one environment
- no surface contradicts the canonical run-state or signal-state model
