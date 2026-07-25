# Axon-X Console UI Layout Lock

**Status:** Locked — 2026-07-04  
**Authority:** [ADR-004](adr/ADR-004-locked-console-shell-layout.md), [ADR-005](adr/ADR-005-operator-sidebar-attention-toggle.md), [ADR-006](adr/ADR-006-operator-command-hero-and-footer-attention.md), [ADR-007](adr/ADR-007-operator-workbench-demotion.md), [ADR-008](adr/ADR-008-ide-shell-content-lock.md) (IDE shell content)  
**Implementation:** `apps/console-web/src/App.vue`, `apps/console-web/src/components/shell/*`, `apps/console-web/src/styles/mockup-shell.css`, `apps/console-web/src/styles/tokens.css`

**Status:** Locked — 2026-07-04 (Operator shell slice through ADR-006)

## Lock Rule

Do **not** rearrange shell regions, resize the primary grid, or change dock seam order
without a new ADR that supersedes ADR-004.

Allowed without a layout ADR:

- DTO-backed content inside existing regions
- visual polish inside existing seams (typography, color, motion)
- wiring new hosts into existing tabs/panels (terminal, problems, conversation)
- bug fixes that restore this document's geometry

Disallowed without a layout ADR:

- moving KAIRO Briefing above Run/Approvals/Signals
- splitting or merging top-level regions
- replacing the five-region shell with alternate navigation
- introducing a separate bottom-panel grid row (terminal stays inside center workbench)

## Shell Grid

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ TOPBAR (58px)                                                                │
├──────────────┬───────────────────────────────────────────────┬───────────────┤
│ LEFT SIDEBAR │ CENTER WORKBENCH                              │ RIGHT DOCK    │
│ ~20%         │ ~55%                                          │ ~25%          │
│              │  editor tabbar + breadcrumb + Monaco           │  upper stack  │
│              │  ───────────────────────────────────────────  │  (scroll)     │
│              │  bottom terminal dock (resizable)             │  KAIRO hero   │
├──────────────┴───────────────────────────────────────────────┴───────────────┤
│ STATUS BAR (30px)                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

CSS owner: `.console-shell--mockup` in `mockup-shell.css`

| Token | Value |
|---|---|
| `--topbar-height` | `58px` |
| `--statusbar-height` | `30px` |
| `--shell-gutter` | `0.85rem` |
| Column template | `minmax(240px, 20%) minmax(0, 55%) minmax(300px, 25%)` |

Boot sequence: optional `BootWakeOverlay` before shell render (skippable; respects reduced motion).

## Region Map

| Region | Component | Grid area |
|---|---|---|
| Top bar | `shell/TopBar.vue` | `topbar` |
| Left sidebar | `shell/LeftSidebar.vue` | `leftSidebar` |
| Center workbench | `shell/CenterWorkbench.vue` | `centerWorkbench` |
| Right dock | `shell/RightDock.vue` | `rightDock` |
| Status bar | `shell/StatusBar.vue` | `statusBar` |

State owner: `apps/console-web/src/stores/shell.ts` (single Pinia store).

## Top Bar (locked)

Grid columns left → right:

1. **Identity zone** — brand block + context panel
2. **Runtime strip** — up to three DTO chips (`run`, `watch`, `degraded`)
3. **KAIRO presence module** — clickable; scrolls/focuses briefing seam
4. **Controls** — Operator / IDE toggle + settings affordance

Identity zone contents:

- Brand: `AXON-X` + `OPERATOR CONSOLE`
- Context panel: mockup breadcrumb row + runtime version chip bar (`RUNTIME` label + KAIRO.CODE / POLICY / AXON-X version chips)

Runtime strip source: `buildTopbarChips()` in `runtime-strip.ts`.

## Left Sidebar (locked)

### Operator mode

Top → bottom:

1. **Primary panel toggle** — `WORKSPACES | ATTENTION` (mirrors dock hero toggle pattern)
2. **Workspaces view** — filter, workspace list, `+ New Workspace`
3. **Attention view** — Active Run, Approvals, Signals (`AttentionStackPanel`)
4. **Workspace status card** — radar widget + four runtime-backed status rows (pinned in both views)

### IDE mode (ADR-008)

Top → bottom:

1. **Activity bar** — Explorer (default), Search/Git stubs, Terminal focus, Agent dock focus (`IdeActivityBar`, 42px)
2. **Explorer column** — `WorkspaceFileTree` in `IdeExplorerPanel`; collapsible via Ctrl/Cmd+B
3. **KAIRO sidebar anchor** — `KairoSidebarPanel` pinned footer (**replaces** workspace status card in IDE)

Workspaces move to **agent dock header tabs** (`AgentDockWorkspaceTabs`). Runtime status rows
appear on status bar + topbar chips only — not the left footer.

Workspace catalog currently filters to mockup workspace IDs for presentation parity.

## Center Workbench (locked)

Shared region; **content differs by layout mode** (ADR-007).

### Operator mode (ADR-007)

Authoritative detail: [OPERATOR_MISSION_CONTROL_V1.md](OPERATOR_MISSION_CONTROL_V1.md)

Top → bottom inside one region:

1. **Mission control panel** (`OperatorStatusRadarPanel.vue`) — execution theater, not a
   second dashboard. Regions:
   - **Header** — title, terminal chip, KAIRO presence dot
   - **Execution stage (hero)** — phase tag, run id, elapsed, progress bar, current step,
     briefing notice; idle standby when no active run
   - **Live execution feed** — scrollable receipts + current step + agent excerpt (max 6 items;
     hidden when idle with no history)
   - **Run controls** — STOP / RESUME / COMPLETE / APPROVE / REJECT wired to shell store
   - **Utility actions** — Open Attention, Open KAIRO Briefing
   - **Status rail** — Watch, Signals, Approvals, Control plane, Workspace (compact)
   - **Terminal dock strip** — when terminal collapsed: full-width reopen bar
2. **Terminal dock** — same bottom resizable panel as IDE (`TERMINAL | PROBLEMS | OUTPUT | LOGS`,
   session-persisted height, resize handle), **collapsible in Operator**.

Editor stack is hidden in Operator mode. Mission control owns the upper workbench.

**Terminal defaults (Operator):**

| Setting | Value |
|---|---|
| First-visit default | **Hidden** |
| Session key | `axon-x-workbench-terminal-panel-visible-v1:operator` (mode-specific; independent of IDE) |
| Default height when open | ~20% of workbench (`OPERATOR_WORKBENCH_TERMINAL_HEIGHT_RATIO`) |
| Reopen | Header **Open terminal** chip, bottom **Terminal dock · Show** strip, or chip toggle |
| Close | Terminal tab-bar ✕ (same as IDE) |

**Not in v1:** Operator Ctrl/Cmd+J terminal shortcut; auto-reveal on executing PTY runs;
rich tool stdout/diff in feed (requires control-plane run-step events). See v1 limitations in
`OPERATOR_MISSION_CONTROL_V1.md`.

### IDE mode

Top → bottom inside one region:

1. **Editor stack**
   - file tab bar
   - workbench toolbar (`New file`, `Rename active file`, split/change placeholders)
   - workspace/file breadcrumb
   - Monaco editor (`EditorHost`)
   - inline editor status strip
2. **Bottom dock** (resizable height, session-persisted; collapsible in IDE)
   - tab bar: `TERMINAL | PROBLEMS | OUTPUT | LOGS`
   - workspace connection label
   - `TerminalHost` (xterm + backend PTY) when Terminal tab active
   - **Close panel** (IDE only) hides the dock so the editor fills the workbench; **Show terminal**
     affordance in the editor status bar restores the dock with the last session height

Terminal dock height syncs to KAIRO briefing seam via `--briefing-dock-height` (see right dock).

Column height sync: `shell-column-layout.ts` + `CenterWorkbench` resize observer align left sidebar, workbench, and right dock to the status bar top edge.

## Right Dock (locked)

### Operator mode (ADR-005 + ADR-006)

Structure:

```text
dock-stack
├── dock-stack__upper (conversation-first)
│   └── Conversation (expanded by default)
└── DOCK HERO (bottom-anchored)
    └── Command ↔ KAIRO toggle (`DockHeroPanel`)
        ├── Command: bottom-anchored autosize composer (`CommandSeamPanel`)
        └── KAIRO: briefing hero (`BriefingPanel`, min 188px)
```

Run / Approvals / Signals live in the left sidebar **Attention** view.

Command hero rules (ADR-006):

- Composer auto-grows 2–8 lines via `command-composer-autosize.ts`
- Hero height grows with composer up to `min(42vh, 22rem)`; min `188px`
- No in-hero KAIRO attention ribbon in Command mode
- No **SWITCH TO COMMAND** button in KAIRO hero (toggle only)

Footer KAIRO CTA (ADR-006): when briefing attention is active and hero mode is
**Command**, a glowing **OPEN KAIRO BRIEFING** button renders in the status bar
**right column** (aligned under the hero), calling `focusKairoBriefing()`.

### IDE mode (ADR-008 — agent dock)

Structure:

```text
agent-dock (replaces dock-stack in IDE)
├── header — AGENT DOCK title + workspace tabs
├── attention-rail — compact run / approvals / signals pills + STOP
├── transcript — `ConversationSeamPanel` (primary surface)
└── composer — pinned `CommandSeamPanel`
```

No `AttentionStackPanel`, `HudSeamCard` seams, or `DockHeroPanel` in IDE mode.
KAIRO narrative lives in left sidebar `KairoSidebarPanel` + topbar `KairoPresenceBar`.

Center workbench (IDE only): bottom terminal panel may be **closed** via tab-bar action;
editor fills the workbench until the status-bar **TERMINAL** chip restores the panel.
Right dock stack is unchanged when the center panel is collapsed.

Seam order is **identical in IDE mode**. The bottom hero stays
**anchored at the bottom** of the dock; the upper seams scroll above it.
Command and KAIRO Briefing **share the hero slot** and interchange via a header toggle.

KAIRO Briefing (IDE + Operator KAIRO tab):

- hero treatment (`.hud-seam--hero`)
- Operator KAIRO tab: min height `188px`; IDE hero height capped via `computeHeroDockHeight()`
- `BriefingPanel` hero mode: Notice + Advise + reactor; no bottom switch-to-command CTA

`ConversationSeamPanel` lives in the upper stack. Command and KAIRO share the bottom
hero via `DockHeroPanel` (header toggle). Chat APIs: `POST /api/chat/messages`, `GET /api/workspaces/{workspace_id}/chat/thread`,
and `GET /api/chat/threads/{thread_id}/history`. Empty workspace thread lookup returns HTTP 200 with null `thread_id` (not 404).

Seam titles use operator-facing copy from `dock-seam-layout.ts` (`Active Run`, `Approvals`, etc.).

## Status Bar (locked)

Three-column grid aligned with shell columns (`status-bar-mockup__grid`):

| Column | Content |
|---|---|
| Left + center (span 2) | HUD frame: watch chip, run phase, signals, workspace, clock |
| Right (hero rail) | Optional **OPEN KAIRO BRIEFING** glowing CTA when Command mode + briefing attention active |

Source: `buildStatusBarZones()` in `mockup-shell-view.ts`; attention CTA in `StatusBar.vue`.

## Workspace and terminal session (locked)

- Operator workspace pick is **pinned** in session storage (`operator-workspace-selection.ts`);
  run refresh must not override manual sidebar selection.
- Terminal attach **clears buffer** before restoring per-workspace scrollback
  (`create-xterm-session.ts`).
- Terminal panel visibility is **mode-specific** in session storage:
  `axon-x-workbench-terminal-panel-visible-v1:operator` (default hidden) and
  `:ide` (default visible). See `workbench-terminal-split.ts`.
- Chat thread rehydration is workspace-scoped via `loadWorkspaceThread()`.

## Layout Modes

| Mode | Geometry | Difference |
|---|---|---|
| `operator` | same grid | left sidebar `WORKSPACES \| ATTENTION` toggle; right dock conversation-first |
| `ide` | same grid | explorer tree visible; right dock retains Run → Approvals → Signals → Conversation |

Both modes share regions, DTOs, and the bottom Command/KAIRO hero.

## Visual System

Locked presentation bundle:

- `mockup-shell.css` — geometry, HUD seams, dock/topbar/sidebar chrome
- `tokens.css` — surfaces, accent, motion, shell dimensions
- `UI_VISUAL_DIRECTION.md` in frozen planning — north star for polish inside regions

HUD corner brackets: hidden on sidebar panels; visible on dock seams only.

## Verification

Layout-sensitive changes must pass:

```bash
npm run verify
```

Future optional guard: screenshot/fitness check against this document's region geometry.

## Related Docs

- Frozen planning: `axon-local/Plans/Axon-Watch/UI_SPEC.md`, `UI_COMPOSITION_SPEC.md`, `UI_VISUAL_DIRECTION.md`
- ADR: `docs/adr/ADR-004-locked-console-shell-layout.md`
- ADR: `docs/adr/ADR-005-operator-sidebar-attention-toggle.md`
- ADR: `docs/adr/ADR-006-operator-command-hero-and-footer-attention.md`
- ADR: `docs/adr/ADR-007-operator-workbench-demotion.md`
- Operator mission control v1: `docs/OPERATOR_MISSION_CONTROL_V1.md`
- Handbook: `docs/HOW-TO-HANDBOOK.md` → **Locked Shell Layout**
