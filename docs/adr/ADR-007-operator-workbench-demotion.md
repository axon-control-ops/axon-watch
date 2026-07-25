# ADR-007: Operator Workbench Demotion

## Status

Accepted

## Context

ADR-005 and ADR-006 locked Operator layout around conversation-first right dock,
sidebar attention toggle, and a bottom-anchored Command/KAIRO hero with autosize
composer and footer briefing CTA.

Operator review still shows the **center workbench dominated by Monaco** even
though Operator mode is a control-plane surface: workspace context, terminal,
and operator dialogue matter more than sustained file editing. IDE mode already
owns full editor + explorer semantics.

ADR-004 locked shared five-region geometry across Operator and IDE; it did not
require identical **content** inside the center workbench. ADR-005 established
precedent for mode-specific region contents without changing the grid.

## Decision

**In Operator mode, demote the center editor stack and replace it with a dedicated
mission/control surface.**

Locked Operator center workbench target:

1. **Hide** Monaco editor stack by default in Operator mode (tab bar, breadcrumb,
   editor host, inline editor status strip) — **shipped (phase 1)**.
2. **Mission control panel v1 (shipped — phases 2 and 3, refined 2026-07-05)** —
   `OperatorStatusRadarPanel.vue` is an **execution theater**: hero stage (phase,
   progress, current step, notice), live execution feed, direct run controls, compact
   status rail, and terminal reopen affordances. Full specification:
   [`docs/OPERATOR_MISSION_CONTROL_V1.md`](../OPERATOR_MISSION_CONTROL_V1.md).
3. **Terminal dock stays docked, but is collapsible in Operator and IDE** —
   Operator default **hidden** on first visit; mode-specific session keys; reopen via
   header chip + bottom dock strip; close via tab-bar ✕. IDE default visible with
   status-bar **TERMINAL** chip to restore when collapsed.
4. **IDE mode** — full editor stack + explorer + agent dock; bottom terminal panel
   collapsible as above.
5. **ADR-007 complete** — terminal-first promotion and read-only preview are no
   longer required outcomes of this ADR. Reopening those ideas requires a new ADR.

Grid geometry, column proportions, and region map remain ADR-004.

## Alternatives Considered

1. **Keep editor visible in Operator** — rejected after ADR-005/006 review; steals
   horizontal space from conversation/command story without operator benefit.
2. **Swap center and right columns** — rejected; larger layout shock than workbench
   demotion; conflicts with locked column roles.
3. **Third top-level shell mode** — rejected; Operator/IDE toggle is sufficient.
4. **Dense telemetry dashboard in center (phase 2/3 prototype)** — rejected after
   operator review; duplicated topbar/status bar/dock truth and violated “evidence
   surface, not primary status” guidance in `UI_REFERENCE_ARCHETYPES.md`.

## Trade-Offs

- **Gain:** Operator center focuses on runtime action and review flow instead of file editing.
- **Gain:** Terminal can be hidden without switching to IDE; mission control fills the void.
- **Gain:** Direct run mutations available in center without opening Attention sidebar.
- **Cost:** Operator still does not offer inline file editing or read-only preview in the center.
- **Cost:** v1 feed depth is limited to receipt labels until control-plane streams richer steps.

## Consequences

- `CenterWorkbench.vue` hides the editor stack when `layoutMode === 'operator'`.
- `OperatorStatusRadarPanel.vue` is the primary Operator mission/control surface.
- `operator-status-radar-view.ts` owns DTO projections for stage, feed, and rail.
- `workbench-terminal-split.ts` persists terminal visibility per layout mode.
- `UI_LAYOUT_LOCK.md` and `OPERATOR_MISSION_CONTROL_V1.md` document Operator center behavior.

## v1 Follow-ups (not ADR-007 blockers)

Documented in `OPERATOR_MISSION_CONTROL_V1.md` § v1 Limitations:

- Rich execution feed (tool args, stdout, diffs) from run-step events
- Auto terminal peek when active run uses PTY
- Reduced duplication between status rail and HUD (optional slimming)

Shipped after ADR acceptance: Operator **Ctrl/Cmd+J** terminal toggle (shared with IDE).

## Reevaluation Triggers

Reopen if:

- operator testing shows frequent in-place file edits are blocked without IDE toggle.
- terminal-first layout breaks PTY height sync or column alignment regressions.
- product adds a dedicated "quick edit" operator affordance that supersedes demotion.

## Notes

- Does not change ADR-005 sidebar attention or ADR-006 hero/footer contracts.
- **Operator void:** closed by mission control v1 and terminal collapse parity.
- Frozen planning reference: `axon-local/Plans/Axon-Watch/UI_SPEC.md` Operator
  vs IDE intent.
