# Operator Mission Control — v1 Specification

**Status:** Shipped (v1) — 2026-07-05  
**Authority:** [ADR-007](adr/ADR-007-operator-workbench-demotion.md)  
**Implementation:** `apps/console-web/src/components/shell/OperatorStatusRadarPanel.vue`, `apps/console-web/src/lib/operator-status-radar-view.ts`, `apps/console-web/src/components/shell/CenterWorkbench.vue`, `apps/console-web/src/lib/workbench-terminal-split.ts`  
**Layout lock:** [UI_LAYOUT_LOCK.md](UI_LAYOUT_LOCK.md) → Center Workbench → Operator mode

## Purpose

In **Operator** layout mode, the center workbench does not host Monaco. Instead it hosts a
**mission control surface** that answers one question for the operator:

> **What is Axon doing right now, and what can I do about it?**

v1 is an **execution theater**, not a second dashboard. Status truth remains owned by the
top bar, status bar, left Attention sidebar, and right dock. The center surface shows
**live execution narrative + direct run actions + evidence feed**, with the terminal as an
optional bottom dock.

## Scope Boundaries

| Owns (center) | Does not own (other regions) |
|---|---|
| Primary run phase, current step, progress | Full approvals list (left Attention) |
| Live execution feed (receipts + agent excerpt) | Full conversation transcript (right dock) |
| Direct run mutations (stop/resume/complete/approve/reject) | KAIRO briefing hero (right dock / left KAIRO in IDE) |
| Terminal show/hide affordances | Watch/signal drill-down (left Attention + inbox later) |
| Compact secondary telemetry rail | Authoritative run phase chip (status bar + topbar) |

## Component Map

```text
CenterWorkbench (Operator)
├── OperatorStatusRadarPanel.vue     ← mission control (upper workbench)
└── center-workbench__bottom-dock    ← terminal / problems / output / logs (optional)
```

View-model helpers live in `operator-status-radar-view.ts`:

| Helper | Role |
|---|---|
| `operatorExecutionStage()` | Hero block: phase, run id, progress, current step, notice/advise |
| `operatorLiveFeed()` | Scrollable evidence list (max 6 items) |
| `operatorStatusRail()` | Compact 5-cell footer telemetry |
| `operatorRadarTone()` | Panel accent: `nominal` \| `watch` \| `attention` \| `degraded` |

## Panel Regions (top → bottom)

### 1. Header

| Element | Source | Notes |
|---|---|---|
| Title | Static copy | `Mission Control` |
| Terminal chip | `terminalVisible` prop | **Open terminal** when collapsed (accent); **Terminal open** when visible |
| KAIRO presence | `kairoPresenceModuleParts()` | Title + subtitle; static dot (no spinning radar) |

### 2. Execution stage (hero)

Dominates vertical space. One visual story.

| Field | DTO / store source |
|---|---|
| Phase tag | `primaryActiveRun.phase` → `runPhaseTag()` |
| Run id | `primaryActiveRun.run_id` (hidden when idle) |
| Elapsed | `started_at` … `ended_at` \| `updated_at` → `elapsedLabel()` |
| Progress bar | `runPhaseProgress(primaryActiveRun.phase)` |
| Current step | `primaryActiveRun.current_step` \| `summary` \| idle copy |
| Summary | `primaryActiveRun.summary` (active run only) |
| Notice | `operatorBriefing.notice` \| run-aware headline |
| Advise | `operatorBriefing.advise` (idle standby only) |

**Idle modifier** (`operator-status-radar-panel--idle`): centered copy, no progress bar,
no run id, larger standby message when `primaryActiveRun` is null.

**Elapsed formatting (v1):**

- `< 60 min` → `Nm SSs` (e.g. `4m 12s`)
- `≥ 60 min` → `Nh MMm` (e.g. `25h 08m`)
- `≥ 48 h` → `Nd Hh` (e.g. `2d 5h`)

### 3. Live execution feed

Rendered only when `hasActiveRun` **or** pending approvals **or** receipt history exists.

| Item tone | Meaning |
|---|---|
| `done` | Historical receipt from `runHistoryRows` |
| `active` | Current step (`primaryActiveRun.current_step`) |
| `info` | Latest agent message excerpt (deduped vs active step) |
| `pending` | Suggested next action when idle |

Max **6** items. Scrollable (`max-height: min(15rem, 34vh)`).

Header right column shows active `run_id` when present.

### 4. Run controls

Shown when any control is eligible. Wired to `useShellStore()`:

| Button | Store action | Visibility |
|---|---|---|
| STOP RUN | `stopPrimaryRun()` | `can_stop` or phase `executing` |
| RESUME RUN | `resumePrimaryRun()` | `can_resume` |
| COMPLETE RUN | `completePrimaryRun()` | phase `review_ready` |
| APPROVE RUN | `approvePrimaryRun()` | `pendingApprovalsCount > 0` |
| REJECT RUN | `rejectPrimaryRun()` | `pendingApprovalsCount > 0` |

Errors render inline via `runMutationError`. Controls use `flex-shrink: 0` and a top border
so they never overlap the feed.

### 5. Utility actions

Secondary navigation (not run mutations):

- **Open Attention** → `setLeftSidebarMode('attention')` + badge from `leftSidebarAttentionBadgeCount()`
- **Open KAIRO Briefing** → `focusKairoBriefing()`

### 6. Status rail

Five compact cells (not a second hero):

Watch · Signals · Approvals · Control plane · Workspace

Source: `operatorStatusRail()`. **Elapsed is not duplicated here** — it appears only in the
execution stage header when a run is active.

### 7. Terminal dock strip (when terminal collapsed)

Full-width bar at panel bottom:

```text
Terminal dock · {workspace connection label} · Show
```

Click toggles terminal visibility via `@toggle-terminal` → `CenterWorkbench.toggleTerminalPanel()`.

## Terminal Dock (Operator)

The terminal is **inside** `centerWorkbench`, not a separate shell row (ADR-004).

### Defaults (first session, no stored preference)

| Mode | Default visibility | Session key |
|---|---|---|
| `operator` | **Hidden** | `axon-x-workbench-terminal-panel-visible-v1:operator` |
| `ide` | **Visible** | `axon-x-workbench-terminal-panel-visible-v1:ide` |

Keys are **mode-specific**. IDE terminal preference does not force Operator terminal open.

Implementation: `readStoredWorkbenchTerminalPanelVisible(layoutMode)` and
`persistWorkbenchTerminalPanelVisible(layoutMode, visible)` in `workbench-terminal-split.ts`.

### Reopen affordances (Operator, terminal hidden)

1. Header chip — **Open terminal**
2. Bottom strip — **Terminal dock · Show**
3. (When visible) header chip — **Terminal open**; tab-bar ✕ closes

### Close affordances (Operator, terminal visible)

1. Terminal tab-bar close (✕) — same control as IDE
2. Header chip toggles closed

### Height

| Mode | Default height ratio | Notes |
|---|---|---|
| Operator | 20% of workbench | `OPERATOR_WORKBENCH_TERMINAL_HEIGHT_RATIO` |
| IDE | 26% of workbench | `DEFAULT_WORKBENCH_TERMINAL_HEIGHT_RATIO` |

Height and visibility persist in `sessionStorage`. Custom height key:
`axon-x-workbench-terminal-height-v3` (shared across modes).

### Terminal reopen parity

- **Operator:** Mission Control header chip + bottom dock strip; **Ctrl/Cmd+J** toggles the panel.
- **IDE:** Activity bar Terminal button + editor status-bar **TERMINAL** chip; **Ctrl/Cmd+J** toggles the panel.
- Reveal requests bump a shared token; CenterWorkbench persists visibility for the **active** layout mode (Operator and IDE keys stay separate).

### Not in v1

- Auto-reveal terminal when run phase is `executing` with PTY activity
- Inline tool output / diff preview in the live feed (requires richer run-step events from control-plane)

## Visual Tone

Panel root class: `operator-status-radar-panel--{tone}` where tone derives from
degraded state, pending approvals, high/critical signals, and watch connectivity.

**Removed in v1 (vs ADR-007 phase 2/3 prototype):**

- Spinning radar widget in center (motion rule: no ambient always-spinning rings)
- Six-metric grid duplicating status bar
- Tool/output card grid
- Action chip row (Last action / Next action / Risk)
- Separate receipts grid (merged into live feed)

## v1 Limitations (explicit)

v1 closes ADR-007 (editor demotion + mission surface + terminal collapse). It is **not** the
final JARVIS control center.

| Gap | Why it remains |
|---|---|
| Feed is receipt-label depth only | `runHistoryRows` lacks tool args, stdout, diff refs |
| Status rail repeats topbar/status bar counts | Acceptable compact glance; full truth stays in HUD |
| No executing-state motion on hero | Awaiting run-step SSE granularity |
| No auto terminal peek on shell work | Needs run→PTY coupling policy |
| No Operator Ctrl/Cmd+J | Follow-up UX slice |

Reopening terminal-first center promotion or read-only file preview requires a **new ADR**,
not an ADR-007 deferral.

## Verification

```bash
cd apps/console-web
npx vitest run src/lib/operator-status-radar-view.test.ts src/lib/workbench-terminal-split.test.ts
npm run verify   # full gate when touching shell layout
```

Manual acceptance (`TEST-0`):

Automated gate (requires dev stack `./scripts/dev/up.sh`):

```bash
./scripts/verify/test0-workspace-smoke.sh
# or live API slice only:
python3 -m unittest tests.test_test0_workspace_smoke_acceptance -v
```

Checks:

1. `./scripts/dev/check-health.sh` — console-web, control-plane, watch, briefing, inbox, runs, SSE
2. Mission control unit tests — `operator-status-radar-view`, `workbench-terminal-split`
3. Live `workspace_smoke` — briefing Notice/Advise, git status, resume from review, attention DTOs
4. `npm run verify` — full contract + console-web gate

Manual UI checklist (Operator mode on `http://127.0.0.1:4173`):

1. Mission control fills upper workbench; terminal **hidden** on fresh operator session
2. **Open terminal** → bottom dock ~20% height; chip reads **Terminal open**
3. Tab-bar ✕ → dock hides; bottom strip + chip restore reopen path
4. Switch to IDE → terminal follows IDE stored preference independently
5. Active run → hero phase/progress/elapsed; feed lists receipts; STOP visible
6. Idle → centered standby; feed hidden unless history remains

## Related Documents

- [UI_LAYOUT_LOCK.md](UI_LAYOUT_LOCK.md)
- [ADR-007](adr/ADR-007-operator-workbench-demotion.md)
- [MULTITASK-LANES.md](MULTITASK-LANES.md) → ADR-007 p3
- Frozen planning: `axon-local/Plans/Axon-Watch/UI_REFERENCE_ARCHETYPES.md` (Operator center = evidence surface)
