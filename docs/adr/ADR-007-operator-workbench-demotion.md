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

**In Operator mode, demote the center editor stack.** Terminal-first center and upper
workbench content are phased; phase 1 ships editor removal only.

Locked Operator center workbench target:

1. **Hide** Monaco editor stack by default in Operator mode (tab bar, breadcrumb,
   editor host, inline editor status strip) — **shipped (phase 1)**.
2. **Upper workbench status / radar panel (shipped — phase 2 option A)** — `OperatorStatusRadarPanel.vue`
   binds runtime summary, briefing Notice/Advise, active run phase, and connectivity metrics.
   Includes shortcuts to Attention sidebar and KAIRO briefing. Does not host Monaco or IDE
   explorer semantics.
3. **Promote** the bottom terminal dock to primary center surface — **deferred**; terminal
   dock stays bottom-resizable until upper workbench content is decided.
4. **Optional thin slice (follow-up within ADR-007):** read-only file preview
   strip or collapsed editor affordance for situational context — not a full IDE
   editor unless operator explicitly expands to IDE mode.
5. **IDE mode** — full editor stack + explorer + existing right dock; bottom terminal
   panel is **collapsible** (close restores full editor; status-bar **TERMINAL** chip
   resurfaces the dock).

Grid geometry, column proportions, and region map remain ADR-004.

## Alternatives Considered

1. **Keep editor visible in Operator** — rejected after ADR-005/006 review; steals
   horizontal space from conversation/command story without operator benefit.
2. **Swap center and right columns** — rejected; larger layout shock than workbench
   demotion; conflicts with locked column roles.
3. **Third top-level shell mode** — rejected; Operator/IDE toggle is sufficient.

## Trade-Offs

- **Gain:** Operator center focuses on terminal + runtime action; aligns mental
  model (Operator = orchestrate, IDE = edit).
- **Gain:** Conversation and Command hero retain relative prominence without
  shrinking the right dock further.
- **Cost:** Phase 1 leaves a visible **upper workbench void** in Operator mode until
  a follow-up slice fills it (see item 2 above).
- **Cost:** Requires careful height sync so terminal + column layout still align
  with left sidebar and right dock.

## Consequences

- `CenterWorkbench.vue` hides the editor stack when `layoutMode === 'operator'`.
- `OperatorStatusRadarPanel.vue` fills the upper workbench with DTO-backed status/radar.
- Terminal dock behavior is unchanged in Operator; IDE adds collapsible bottom panel.
- `UI_LAYOUT_LOCK.md` amends center workbench and IDE dock sections for Operator vs IDE.

## Reevaluation Triggers

Reopen if:

- operator testing shows frequent in-place file edits are blocked without IDE toggle.
- terminal-first layout breaks PTY height sync or column alignment regressions.
- product adds a dedicated "quick edit" operator affordance that supersedes demotion.

## Notes

- Does not change ADR-005 sidebar attention or ADR-006 hero/footer contracts.
- **Operator void:** filled by the status/radar panel (phase 2). Terminal promotion or
  read-only preview remain optional ADR-007 follow-ups.
- Frozen planning reference: `axon-local/Plans/Axon-Watch/UI_SPEC.md` Operator
  vs IDE intent.