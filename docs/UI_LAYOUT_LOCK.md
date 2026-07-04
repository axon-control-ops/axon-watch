# Axon-X Console UI Layout Lock

**Status:** Locked — 2026-07-04  
**Authority:** [ADR-004](adr/ADR-004-locked-console-shell-layout.md)  
**Implementation:** `apps/console-web/src/App.vue`, `apps/console-web/src/components/shell/*`, `apps/console-web/src/styles/mockup-shell.css`, `apps/console-web/src/styles/tokens.css`

This document records the **current shipped shell geometry and region ownership** as the
layout contract for all future Axon-X console work.

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

Top → bottom:

1. **Workspaces panel** — filter, workspace list, `+ New Workspace`
2. **Explorer** — visible only in `ide` layout mode (`WorkspaceFileTree`)
3. **Workspace status card** — radar widget + four runtime-backed status rows

Workspace catalog currently filters to mockup workspace IDs for presentation parity.

## Center Workbench (locked)

Top → bottom inside one region:

1. **Editor stack**
   - file tab bar
   - workbench toolbar (`New file`, `Rename active file`, split/change placeholders)
   - workspace/file breadcrumb
   - Monaco editor (`EditorHost`)
   - inline editor status strip
2. **Bottom dock** (resizable height, session-persisted)
   - tab bar: `TERMINAL | PROBLEMS | OUTPUT | LOGS`
   - workspace connection label
   - `TerminalHost` (xterm + backend PTY) when Terminal tab active

Terminal dock height syncs to KAIRO briefing seam via `--briefing-dock-height` (see right dock).

Column height sync: `shell-column-layout.ts` + `CenterWorkbench` resize observer align left sidebar, workbench, and right dock to the status bar top edge.

## Right Dock (locked)

Structure:

```text
dock-stack
├── dock-stack__upper (scrollable)
│   ├── Active Run
│   ├── Approvals
│   ├── Signals
│   └── Conversation
└── DOCK HERO (bottom-anchored, fixed height)
    └── Command ↔ KAIRO toggle (`DockHeroPanel`)
```

Seam order is **identical in Operator and IDE mode**. The bottom hero stays
**anchored at the bottom** of the dock; the upper four seams scroll above it.
Command and KAIRO Briefing **share the hero slot** and interchange via a header toggle.

KAIRO Briefing:

- hero treatment (`.hud-seam--hero`)
- height tied to center workbench terminal dock through `--briefing-dock-height`
- `BriefingPanel` inside: KAIRO presence + DTO sections + `OPEN KAIRO CHAT` CTA

`ConversationSeamPanel` lives in the upper stack. Command and KAIRO share the bottom
hero via `DockHeroPanel` (header toggle). Chat APIs: `POST /api/chat/messages`, `GET /api/workspaces/{workspace_id}/chat/thread`,
and `GET /api/chat/threads/{thread_id}/history`. Empty workspace thread lookup returns HTTP 200 with null `thread_id` (not 404).

Seam titles use operator-facing copy from `dock-seam-layout.ts` (`Active Run`, `Approvals`, etc.).

## Status Bar (locked)

Single HUD strip with zones:

- Left: watch status + watch agent label + control-plane version
- Center: run phase + open signal count
- Right: current workspace id
- Tail: UTC clock + shield mark

Source: `buildStatusBarZones()` in `mockup-shell-view.ts`.

## Layout Modes

| Mode | Geometry | Difference |
|---|---|---|
| `operator` | same grid | no explorer tree |
| `ide` | same grid | explorer tree visible under workspaces |

Both modes share regions, DTOs, and dock order.

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
- Handbook: `docs/HOW-TO-HANDBOOK.md` → **Locked Shell Layout**
