# ADR-004: Locked Console Shell Layout

## Status

Accepted

## Context

The Axon-X console shell reached a stable mockup/live geometry after the Phase 3 UI
thin-slice pass:

- five-region grid (topbar, left sidebar, center workbench, right dock, status bar)
- terminal dock embedded inside the center workbench
- right dock with Run → Approvals → Signals above a bottom-anchored KAIRO Briefing hero
- KAIRO presence in the top bar
- Operator / IDE toggle sharing the same geometry

Earlier planning drafts proposed KAIRO Briefing first in Operator mode and a separate
bottom-panel grid row. The implemented shell diverged after operator review: the
bottom-anchored KAIRO card and upper operational seams match the preferred mockup.

Without an explicit lock, parallel agents could reorder dock seams or restructure the
grid and undo verified operator parity.

## Decision

**Lock the current console shell layout as the canonical Axon-X UI geometry.**

Authoritative references:

- `docs/UI_LAYOUT_LOCK.md`
- `apps/console-web/src/App.vue`
- `apps/console-web/src/components/shell/*`
- `apps/console-web/src/styles/mockup-shell.css`
- `apps/console-web/src/styles/tokens.css`

Locked properties:

1. Five-region CSS grid and column proportions (~20% / ~55% / ~25%)
2. Top bar zones: identity (brand + context) | runtime strip | KAIRO module | controls
3. Center workbench: editor stack above resizable terminal dock (no separate shell bottom row)
4. Right dock order: Run, Approvals, Signals, Conversation, Command (upper scroll stack), KAIRO Briefing (bottom hero)
5. Status bar as persistent HUD strip below the main row
6. Operator and IDE modes share geometry; IDE only reveals the explorer tree

Future layout changes require a new ADR superseding this record.

## Alternatives Considered

1. **KAIRO Briefing first in Operator mode** — rejected after operator review; bottom hero preserves scan order for run/signal truth while keeping KAIRO visually prominent.
2. **Separate bottom-panel grid row** — rejected; terminal-inside-workbench matches mockup and keeps column height sync simpler.
3. **Implicit lock via screenshots only** — rejected; insufficient for multi-agent governance.

## Trade-Offs

- **Gain:** stable target for parity, DTO wiring, and parallel Lane B work
- **Gain:** prevents accidental dock reorder regressions
- **Cost:** planning docs that assumed KAIRO-first Operator mode are amended, not deleted
- **Cost:** Conversation / Command seams use local thread state until chat API lands

## Consequences

- `UI_COMPOSITION_SPEC.md` Operator-mode seam order is amended to match implementation
- `UI_LAYOUT_LOCK.md` becomes the implementation-side layout contract
- Lane B agents may polish seams and bind DTOs but must not rearrange regions without ADR-005+
- Terminal ↔ KAIRO height coupling via `--briefing-dock-height` is part of the locked geometry

## Reevaluation Triggers

Reopen layout only if:

- mobile/narrow viewport requires a materially different information architecture
- operator testing shows the bottom KAIRO placement blocks critical run control
- a new product mode (e.g. full-screen IDE) needs a third top-level shell variant approved by product owner

## Notes

- Seam title copy (`RUN SEAM` vs `Active Run`) is presentation polish, not layout
- Mockup workspace catalog filtering is presentation data, not geometry
- **Operator right-dock seam order superseded in part by [ADR-005](ADR-005-operator-sidebar-attention-toggle.md)** (IDE mode retains this ADR's right-dock order)
- Command hero and footer attention locked by [ADR-006](ADR-006-operator-command-hero-and-footer-attention.md)
