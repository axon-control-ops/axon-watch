# ADR-006: Operator Command Hero and Footer Attention

## Status

Accepted

## Context

ADR-005 relocated operational seams and made the Operator right dock
conversation-first. Follow-on operator review refined the Command/KAIRO hero
and footer:

- Command composer was too small and fixed-height; multi-line operator input
  must grow from the bottom anchor.
- The in-hero **KAIRO briefing waiting** ribbon duplicated the header toggle
  and consumed Command space.
- KAIRO briefing hero needed a stable minimum height without redundant CTAs.
- Briefing attention in Command mode belongs in the footer under the hero
  column, not inside the composer stack.
- Workspace-scoped terminal buffers must not leak across sidebar switches.

## Decision

**Lock Operator Command/KAIRO hero behavior and footer attention placement.**

### Command hero (`DockHeroPanel` + `CommandSeamPanel`)

1. Header toggle **Command | KAIRO** remains the only mode switch.
2. Composer is **bottom-anchored** in the hero body.
3. Composer **auto-grows** via `command-composer-autosize.ts`:
   - minimum 2 lines
   - maximum 8 lines in compact hero mode, then internal scroll
4. Command hero panel **height grows** with composer up to `min(42vh, 22rem)`;
   minimum height `188px` (`OPERATOR_HERO_DOCK_HEIGHT_PX`).
5. **No** in-hero KAIRO attention ribbon while Command is active.

### KAIRO briefing hero (`BriefingPanel` hero mode)

1. Minimum hero height `188px`; Notice + Advise + reactor layout inside hero body.
2. **No** bottom **SWITCH TO COMMAND** CTA (header toggle is sufficient).

### Footer attention (`StatusBar.vue`)

1. Status bar uses a **3-column grid** aligned with shell columns.
2. When briefing attention is active **and** dock hero mode is **Command**,
   show a glowing **OPEN KAIRO BRIEFING** button in the **right column**
   (under the hero), not inside the Command stack.
3. Button calls `focusKairoBriefing()`; KAIRO tab badge remains on the hero toggle.

### Workspace session hygiene

1. Operator workspace selection is **pinned** (`operator-workspace-selection.ts`);
   refresh cycles must not override manual sidebar picks.
2. Terminal workspace attach **clears xterm buffer** before restoring
   workspace scrollback (`create-xterm-session.ts`).

## Alternatives Considered

1. **Keep attention ribbon inside Command hero** — rejected; crowds composer.
2. **Fixed-height composer with scroll only** — rejected; poor multi-line UX.
3. **Footer chip inline with status rails** — rejected; misaligned with hero column.

## Trade-Offs

- **Gain:** Command input scales naturally; KAIRO attention is discoverable without
  stealing hero body space.
- **Gain:** Workspace terminal and thread context stay scoped per workspace.
- **Cost:** Command hero can grow and reduce Conversation viewport temporarily.
- **Cost:** Footer gains a second visual row when KAIRO CTA is visible.

## Consequences

- `UI_LAYOUT_LOCK.md` documents hero autosize, footer CTA, and workspace pin.
- `shell-column-layout.ts` owns `computeHeroDockHeight()` and
  `OPERATOR_HERO_DOCK_HEIGHT_PX`.
- IDE mode hero height remains capped separately from Operator command growth rules.

## Reevaluation Triggers

Reopen if:

- autosize hero growth conflicts with mobile/narrow layouts.
- operator requests Command and KAIRO as simultaneous visible panels (not toggle).
- footer CTA placement fails alignment when sidebar width changes materially.

## Notes

- Builds on [ADR-005](ADR-005-operator-sidebar-attention-toggle.md); does not change
  five-region grid or ADR-005 seam relocation.
- **Deferred:** hide/collapse center editor in Operator mode (see ADR-005 alternatives).
