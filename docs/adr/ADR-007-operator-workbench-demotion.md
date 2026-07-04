# ADR-007: Operator Workbench Demotion

## Status

Proposed

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

**In Operator mode, demote the center editor stack; make the workbench
terminal-first with optional read-only file context.**

Locked Operator center workbench target:

1. **Hide** Monaco editor stack by default in Operator mode (tab bar, breadcrumb,
   editor host, inline editor status strip).
2. **Promote** the bottom terminal dock to primary center surface (existing
   resizable terminal panel remains).
3. **Optional thin slice (follow-up within ADR-007):** read-only file preview
   strip or collapsed editor affordance for situational context — not a full IDE
   editor unless operator explicitly expands to IDE mode.
4. **IDE mode unchanged** — full editor stack + explorer + existing right dock.

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
- **Cost:** Quick file edits in Operator require IDE toggle or future preview slice.
- **Cost:** Requires careful height sync so terminal + column layout still align
  with left sidebar and right dock.

## Consequences

- `CenterWorkbench.vue` branches on `layoutMode === 'operator'`.
- `UI_LAYOUT_LOCK.md` amends center workbench section for Operator vs IDE.
- Verification: `npm run verify` + manual smoke on workspace switch, terminal PTY,
  and layout column height sync after editor removal.
- Implementation blocked until this ADR moves to **Accepted** after operator sign-off.

## Reevaluation Triggers

Reopen if:

- operator testing shows frequent in-place file edits are blocked without IDE toggle.
- terminal-first layout breaks PTY height sync or column alignment regressions.
- product adds a dedicated "quick edit" operator affordance that supersedes demotion.

## Notes

- Does not change ADR-005 sidebar attention or ADR-006 hero/footer contracts.
- Frozen planning reference: `axon-local/Plans/Axon-Watch/UI_SPEC.md` Operator
  vs IDE intent.
- Move to **Accepted** when the thin slice lands and manual acceptance passes.
