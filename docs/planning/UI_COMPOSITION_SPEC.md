# AXON-X UI Composition Spec

## Purpose

This document turns the shell layout in [`UI_SPEC.md`](UI_SPEC.md) and the
reference guidance in [`UI_REFERENCE_ARCHETYPES.md`](UI_REFERENCE_ARCHETYPES.md)
into a concrete composition spec for the first polished AXON-X shell slice.

It defines:

- topbar composition
- status bar composition
- right dock composition
- KAIRO presence strip and briefing card
- DTO bindings and empty/degraded states
- delivery slices for Phase 3 UI work

This spec is **presentation-only**. It must not invent alternate truth models.

**Layout lock (2026-07-04):** Shell region geometry and dock seam order are frozen in
`axon-watch/docs/UI_LAYOUT_LOCK.md` and `axon-watch/docs/adr/ADR-004-locked-console-shell-layout.md`.
The sections below are amended where they previously diverged from the locked shell.

Visual north star:

- [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md)
- concept mockup: `assets/axon-x-jarvis-console-mockup.png`

The current functional shell screenshot is the correct geometry. This spec adds
JARVIS-forward chrome, operator-facing copy, and KAIRO hero treatment on top of
that geometry.

## Composition Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOPBAR: brand | workspace trail | runtime strip | KAIRO chip | mode toggle │
├──────────┬──────────────────────────────────────────────┬──────────────────┤
│ LEFT     │ CENTER WORKBENCH                             │ RIGHT DOCK       │
│ SIDEBAR  │ editor host + resizable terminal dock        │ run              │
│ workspaces│                                             │ approvals        │
│ explorer*│                                              │ signals          │
│ status   │                                              │ KAIRO briefing   │
│          │                                              │ (bottom hero)    │
├──────────┴──────────────────────────────────────────────┴──────────────────┤
│ STATUS BAR: watch | run phase | signals | workspace | clock                │
└─────────────────────────────────────────────────────────────────────────────┘

*Explorer visible in IDE mode only. Terminal lives inside center workbench, not a
 separate shell row.
```

Scan order for every mode:

1. topbar global state
2. right dock active exception
3. center workbench evidence/action

## Region Ownership

| Region | Vue feature owner | Primary DTOs |
|---|---|---|
| `topbar` | `console-web/shell/TopBar` | `RuntimeSummary`, layout mode, KAIRO presence |
| `leftSidebar` | `console-web/shell/LeftSidebar` | `WorkspaceRecord[]` |
| `centerWorkbench` | `console-web/shell/CenterWorkbench` | editor host + embedded terminal dock + selected evidence DTO |
| `rightDock` | `console-web/shell/RightDock` | `RunRecord`, `ApprovalRecord`, `InboxItem`, briefing |
| `statusBar` | `console-web/shell/StatusBar` | `RuntimeSummary` projection only |

All regions read from one Pinia shell store. No region may maintain its own
hidden run/signal truth.

## Topbar Composition

Height target: `48px` desktop, `44px` compact/mobile.

### Zone Layout

Left to right:

| Zone | Width | Content | Source |
|---|---|---|---|
| Identity zone | fixed + flex | brand block + context panel | static brand + current mockup breadcrumb/version helpers |
| Runtime strip | flex | active run chip, watch chip, degraded chip | shell projection from `RuntimeSummary` / selected run |
| KAIRO chip | fixed | presence state + optional pulse | KAIRO presence projection (see below) |
| Mode toggle | fixed | `Operator` / `IDE` segmented control | layout store |
| Utility actions | fixed | settings, help, optional voice toggle | local UI state |

Current locked implementation note:

- the context panel still shows a mockup breadcrumb (`Axon-X Bootstrap / bootstrap-model`)
  and fixed version chips for `KAIRO.CODE`, `POLICY`, and `AXON-X`
- only the separate runtime strip is DTO-backed today

### Runtime Strip Rules

Show at most **three** chips in steady state:

1. **Active run chip** — highest-priority active run from `active_runs`
2. **Watch chip** — `watch.connected` + `watch.status`
3. **Degraded chip** — only when `degraded.active === true`

Chip text must use canonical phase/status labels from run-state and
runtime-summary contracts. Do not invent friendlier aliases in the topbar.

Example steady-state chip:

```text
run_641609c4 · executing · Axon-X Bootstrap
watch connected
```

Example degraded chip:

```text
degraded · watch summary stale
```

Click behavior:

- run chip -> focus run seam in right dock
- watch chip -> open signal/watch detail or bottom runtime panel
- degraded chip -> open degraded reasons panel

### KAIRO Topbar Chip

The chip is a compact presence indicator, not a chat entrypoint.

States:

| State | Label | Visual |
|---|---|---|
| `idle` | `KAIRO` | muted accent border |
| `observing` | `KAIRO · observing` | soft pulse on border |
| `listening` | `KAIRO · listening` | accent glow + mic icon |
| `speaking` | `KAIRO · speaking` | accent glow + waveform hint |
| `alerting` | `KAIRO · attention` | semantic high/critical accent |
| `privacy_blocked` | `KAIRO · muted` | muted, no pulse |

Click opens the KAIRO briefing card in the right dock.

Voice/listening states are presentation only. They must reflect operator
presence settings and current attention policy, not invent activity.

## Status Bar Composition

Height target: `24px`.

Left to right (locked implementation):

| Zone | Content | Source |
|---|---|---|
| Left HUD chip | watch connectivity + watch status + control-plane version | `RuntimeSummary.watch`, `RuntimeSummary.control_plane.version` |
| Center chips | run phase + signal count | selected run + `RuntimeSummary.signals` |
| Right chip | current workspace id | active `WorkspaceRecord` |
| Tail | UTC clock + shield mark | local UI time |

Rules:

- status bar is a compact HUD strip, not a full textual summary of every runtime seam
- semantic colors are currently used for watch success/warning, run phase brand,
  and signal warning states
- layout mode and approvals counts are not rendered as standalone status segments
  in the locked implementation yet

## Right Dock Composition

Default width: `360px` desktop, `320px` compact, full-width overlay on narrow
viewports.

### Default Seam Order (IDE mode)

1. **Active Run**
2. **Approvals**
3. **Signals**
4. **KAIRO Briefing**

### Operator Mode Seam Order (locked)

Operator and IDE modes share the same seam order. KAIRO Briefing is the **bottom**
visual hero, not the first seam:

1. **Active Run**
2. **Approvals**
3. **Signals**
4. **Conversation**
5. **Command**
6. **KAIRO Briefing** — bottom-anchored hero; height coupled to workbench terminal dock

Upper five seams scroll inside `dock-stack__upper`. Conversation and Command are
part of the locked upper stack (orders 4–5), backed by control-plane chat endpoints.

Only one seam may use hero chrome at a time. Hero emphasis must not remove the other
seams from the dock column.

### Operator-Facing Seam Titles

The locked implementation ships operator-facing titles from
`apps/console-web/src/lib/dock-seam-layout.ts` via `shell.dockSeamState()`:

| Internal/dev name | Operator-facing title | Status (2026-07-04) |
|---|---|---|
| Run seam | `Active Run` | **verified** in `RightDock.vue` |
| Approvals seam | `Approvals` | **verified** |
| Signals seam | `Signals` | **verified** |
| KAIRO briefing card | `KAIRO Briefing` | **verified** (`DockHeroPanel`) |
| Thread seam | `Conversation` | **verified** |
| Composer seam | `Command` | **verified** (bottom hero toggle) |

Dev scaffold labels (`RUN SEAM`, etc.) are no longer shown in the default shell.

See [`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md) for full copy rules.

### 1. Run Seam

Purpose: show the currently selected or highest-priority active run.

Required fields:

- `run_id`
- `phase`
- `status`
- `title`
- `detail` or latest step label
- primary actions: stop, resume, open full run

Hero behavior:

- auto-promoted when run enters `executing`, `awaiting_approval`, or blocked state
- in IDE mode, remains visible but compact unless expanded

Empty state:

```text
No active run
Start a run from Command or choose a workspace action.
```

### 2. Approvals Seam

Purpose: surface guarded actions requiring operator decision.

Required fields:

- approval title
- severity
- linked run/workspace
- approve / reject actions

Hero behavior:

- auto-promoted when `approvals.pending_count > 0` and no higher-severity run
  block exists

Empty state:

```text
No pending approvals
```

### 3. Signals Seam

Purpose: show top ranked inbox/signal items without replacing the full inbox
API.

Required fields per row:

- `signal_id`
- severity
- status
- title
- `watch_rule.mode` when present

Show at most **3** rows in the dock. Full list lives in inbox surface later.

Hero behavior:

- auto-promoted on new interruptive signal with `watch_rule.interrupts === true`

Empty state:

```text
No open signals
Watch is connected and monitoring.
```

### 4. KAIRO Briefing Card

Purpose: concise operator-facing summary from control-plane briefing projection.

This is the main KAIRO presence surface in v1.

Suggested fields:

- `headline`
- `notice`
- `advise`
- `next_safe_action`
- `pending_approvals_count`
- `active_runs_count`
- `top_signal_title`
- `degraded_summary`
- `generated_at`

Card sections:

| Section | Purpose |
|---|---|
| Headline | one-line current operator situation |
| Notice | what changed or needs awareness |
| Advise | recommended next review/action |
| Footer actions | open approvals, open signal, open run, toggle spoken alerts |

Rules:

- card copy may use KAIRO persona phrasing
- counts, phases, severities, and action eligibility must come from DTOs
- card must degrade gracefully to runtime-summary-only content before briefing
  API exists

Empty/degraded state:

```text
KAIRO briefing unavailable
Showing runtime summary only.
```

### 5. Thread Seam

Purpose: compact transcript context for the active run/thread.

Skeleton phase may show:

```text
No active conversation
```

Do not duplicate a full chat product inside the dock in v1.

### 6. Composer Seam

Purpose: single composer entrypoint for operator intent.

Rules:

- one composer model for the whole app
- composer attaches to active workspace/run context
- no second composer elsewhere in the shell

Skeleton phase may show placeholder input with disabled submit until run/chat
APIs are wired.

## Operator vs IDE Dock Emphasis

| Seam | Operator mode | IDE mode |
|---|---|---|
| Run | expanded by default when active | compact summary |
| Approvals | expanded when pending | compact badge + expand on click |
| Signals | expanded when interruptive | compact list |
| KAIRO briefing | default bottom hero | collapsed to chip + expandable card |
| Thread | expanded | compact |
| Composer | visible | visible, shorter |

Both modes use the same seams and DTOs.

## KAIRO Presence System

KAIRO presence is composed from four UI primitives:

1. topbar chip
2. briefing card
3. optional spoken-alert strip under topbar
4. dock attention badge on signals/approvals seams

### Spoken-Alert Strip

Only visible when:

- spoken alerts enabled
- privacy mode allows
- an interruptive signal or approval is eligible

Content:

```text
Attention required · {title} · Speak · Open · Dismiss
```

Must bind to canonical signal/approval IDs.

### Presence Settings Preset

The old JARVIS toggle becomes **Enable KAIRO preset**, which sets:

- `operator_persona_enabled`
- `spoken_alerts_enabled`
- `ambient_presence_enabled`
- optionally `hands_free_enabled`

Preset must not bypass approval boundaries or privacy mode.

## Design Tokens

Use the full JARVIS-forward token system in
[`UI_VISUAL_DIRECTION.md`](UI_VISUAL_DIRECTION.md).

Minimum shell tokens required in UX-0:

- base surfaces (`--surface-shell`, `--surface-panel`, `--surface-panel-elevated`)
- glass/HUD chrome (`--glass-blur`, `--border-hud`, `--glow-hud-soft`)
- text hierarchy
- cyan brand accent (`--accent-brand`)
- semantic status colors
- motion tokens with reduced-motion fallbacks
- HUD corner bracket treatment for hero seams

## Empty, Loading, and Degraded States

Every seam must define all three states explicitly.

| State | Shell behavior |
|---|---|
| Loading | render region chrome immediately; show seam skeleton, not blank panels |
| Empty | concise operator-readable message + one next action |
| Degraded | preserve layout; show degraded chip/strip; never fake green status |

If `RuntimeSummary` loads but briefing API fails:

- keep topbar/status bar truthful
- show degraded KAIRO card fallback
- do not block editor/dock render

## Data Flow

Boot sequence:

1. settings/config bootstrap
2. workspace list
3. `GET /api/runtime/summary`
4. render topbar, status bar, dock skeleton
5. subscribe to `GET /api/live/events`
6. fetch `GET /api/briefing` when KAIRO card visible
7. hydrate run/approval/signal seams from summary + live events

Live update rule:

- SSE updates mutate shell store
- UI regions re-render from store projections
- no per-component polling in v1

## Delivery Slices

### UX-0 — Tokens, boot sequence, and shell hierarchy

Deliverables:

- JARVIS-forward semantic design tokens
- glass/HUD panel primitives with corner brackets
- boot / wake sequence
- topbar/status bar/dock region components
- operator-facing seam titles
- scan hierarchy documented in Storybook or dev preview

Exit criteria:

- the shell renders cleanly from `RuntimeSummary` with JARVIS-forward chrome
- boot sequence can be skipped and respects reduced motion
- operator-facing seam titles replace dev scaffold labels in default view

### UX-1 — Runtime-backed topbar and status bar

Deliverables:

- runtime strip chips
- watch/degraded indicators
- status bar projections

Exit criteria:

- `RuntimeSummary` alone drives topbar/status bar with no hidden fetches

### UX-2 — Right dock seams

Deliverables:

- run, approvals, signals, thread, composer seams
- hero promotion rules
- empty/loading/degraded states

Exit criteria:

- one active run and one open signal render consistently in dock + status bar

### UX-3 — KAIRO presence layer

Deliverables:

- topbar KAIRO chip
- briefing card
- spoken-alert strip stub
- preset settings mapping

Exit criteria:

- briefing card falls back safely before briefing API exists
- KAIRO states never contradict run/signal truth

### UX-4 — Live update polish

Deliverables:

- SSE-driven seam updates
- interruptive signal hero promotion
- reduced-motion behavior

Exit criteria:

- run phase change visible in topbar, status bar, and dock within documented
  fitness budget

## Acceptance Criteria

This composition spec is being followed when:

- the shell in the screenshot geometry can evolve into a JARVIS-forward command
  center without restructuring regions
- topbar, status bar, and dock show the same truth
- KAIRO briefing is the Operator-mode hero without blocking IDE work
- operator-facing copy replaces dev seam labels in production surfaces
- every seam has explicit DTO binding and empty/degraded behavior
- Phase 3 UI work can proceed slice-by-slice without reopening layout decisions
