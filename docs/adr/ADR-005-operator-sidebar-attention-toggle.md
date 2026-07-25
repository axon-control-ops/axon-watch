# ADR-005: Operator Sidebar Attention Toggle

## Status

Accepted

## Context

Operator review showed the right dock was overloaded: Run, Approvals, Signals,
Conversation, and Command/KAIRO competed for ~25% column width. Conversation
and Command felt cramped; operational seams duplicated glance data already on
the status bar and top runtime strip.

ADR-004 locked the five-region grid and right-dock seam order. It did not
forbid mode-specific content assignment inside regions. Operator testing
triggered the ADR-004 reevaluation path for seam ownership without changing
grid geometry.

## Decision

**In Operator mode, move Run / Approvals / Signals into the left sidebar behind
a `WORKSPACES | ATTENTION` toggle; make the right dock conversation-first.**

Locked Operator layout:

1. **Left sidebar (Operator)** — header toggle `WORKSPACES | ATTENTION`
   - Workspaces view: filter, workspace list, new workspace affordance
   - Attention view: Active Run, Approvals, Signals (compact stack)
   - Workspace status card pinned at bottom in both views
2. **Right dock (Operator)** — upper stack: Conversation (expanded by default)
   - bottom hero: Command ↔ KAIRO (`DockHeroPanel`)
3. **IDE mode unchanged** — left sidebar keeps Workspaces + Explorer; right
   dock keeps Run → Approvals → Signals → Conversation + hero toggle

The five-region grid, column proportions, and status bar remain as ADR-004.

## Alternatives Considered

1. **Reorder right dock only** — rejected; insufficient space without moving ops seams.
2. **Collapse editor in Operator** — deferred; orthogonal to attention relocation.
3. **Three-way left toggle (Workspaces | Attention | Explorer)** — rejected for Operator; IDE already stacks Explorer.

## Trade-Offs

- **Gain:** Conversation and Command/KAIRO get dedicated vertical space in Operator mode.
- **Gain:** Workspaces and operational truth share one column with a learnable toggle pattern.
- **Cost:** Operator must toggle to switch between workspace picking and run/approval review.
- **Cost:** ADR-004 right-dock seam order applies to IDE mode only.

## Consequences

- `UI_LAYOUT_LOCK.md` amended for Operator vs IDE region contents.
- `LeftSidebar.vue` owns Operator attention toggle; `AttentionStackPanel.vue` shares ops seams.
- `RightDock.vue` renders conversation-first stack in Operator mode.
- `dock-seam-layout.ts` keeps Conversation expanded in Operator mode.
- `shell.ts` stores `leftSidebarMode` with smart default to ATTENTION when approvals or interruptive signals exist.

## Reevaluation Triggers

Reopen if:

- Operator testing shows the sidebar toggle blocks critical workspace switching during incidents.
- mobile/narrow viewport needs a different attention surface.
- a third layout mode requires divergent seam ownership again.

## Notes

- Supersedes ADR-004 §Decision item 4 (right-dock seam order) for **Operator mode only**.
- IDE mode retains ADR-004 right-dock order.
- Status bar and top runtime strip remain persistent glance layers.
