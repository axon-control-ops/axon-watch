# ADR-008: IDE Shell Content Lock — Agent Dock + KAIRO Sidebar Anchor

## Status

Accepted — 2026-07-05

## Context

ADR-004 locks five-region shell geometry across Operator and IDE modes. ADR-007
demotes the Operator center workbench editor stack while IDE mode owns full editor
+ explorer semantics.

axon-local IDE mode places transcript and composer in a right **agent dock** and
keeps coding surfaces center-weighted (`docs/architecture/axon-console-ide-mode.md`).

Before this ADR, `axon-watch` IDE mode incorrectly mounted operator ops seams in
the right dock (`AttentionStackPanel`, `DockHeroPanel`) and duplicated runtime
truth in a **workspace status card** left footer.

KAIRO is the operator presence layer. In IDE mode it must stay visible without
occupying the agent dock or a bottom Command/KAIRO hero.

## Decision

1. **IDE right dock** becomes **Agent Dock** only: workspace tabs, compact attention
   rail, transcript, pinned composer. No `AttentionStackPanel`, no `DockHeroPanel`,
   no `HudSeamCard` seams in IDE.
2. **IDE left sidebar footer** becomes **KAIRO sidebar anchor** (`KairoSidebarPanel`),
   **replacing** the workspace status card. Same pinned anchor slot
   (`left-sidebar-mockup__status-anchor`).
3. **IDE left sidebar body** uses activity bar + file explorer (workspaces move to
   agent dock header tabs).
4. **Operator mode** is unchanged: workspace status card remains; right dock remains
   conversation-first + Command/KAIRO hero per ADR-005/ADR-006.
5. Workspace status DTO rows (`workspaceStatusCardRows`) are **Operator-only**
   left-sidebar content. In IDE, equivalent truth lives on status bar + topbar chips.

## Alternatives Considered

1. Keep workspace status in IDE — rejected; duplicates status bar.
2. KAIRO only in topbar — rejected; too compact for long IDE sessions.
3. KAIRO as right-dock hero — rejected; conflicts with agent-dock composer-first parity.
4. Keep ops seams in IDE right dock — rejected; conflicts with axon-local agent dock parity.

## Trade-Offs

- **Gain:** IDE matches Cursor/VS Code mental model (explorer | editor | agent).
- **Gain:** KAIRO presence anchored without stealing composer space.
- **Cost:** Requires ADR-amended `UI_LAYOUT_LOCK.md` and new bounded components.
- **Cost:** IDE ops detail is compact (attention rail) rather than full HUD seams.

## Consequences

- New components: `KairoSidebarPanel`, `AgentDock`, `IdeActivityBar`, `IdeExplorerPanel`.
- `LeftSidebar.vue` and `RightDock.vue` branch on `layoutMode`.
- `UI_LAYOUT_LOCK.md` IDE sections amended.
- Parity ledger IDE row updated.

## Reevaluation Triggers

- IDE users report missing workspace status not covered by status bar.
- KAIRO footer competes with explorer height on short viewports.
- Agent dock transcript/composer ergonomics fail parity with axon-local.

## Notes

- Supersedes IDE content sections of prior `UI_LAYOUT_LOCK` right-dock and left-footer docs.
- Does not change ADR-004 column geometry.
