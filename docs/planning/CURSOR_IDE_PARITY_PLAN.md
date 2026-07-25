# Cursor IDE parity — project plan

Status: **proposed follow-on project** (not in scope for `feat/mission-control-holographic`).
Owner: TBD. Do not expand holographic / Mission Control PRs into this plan.

## Goal

Decide and deliver a bounded “Cursor-class IDE” experience inside Axon console IDE mode,
with explicit non-goals so “looks like Cursor” is not mistaken for “is Cursor.”

## Non-goals (v1)

- VS Code / Cursor extension marketplace compatibility
- Cursor Cloud Agents / `@cursor/sdk` product clone
- Full multi-root workspace UX parity
- Pixel-perfect clone of Cursor chrome (tabs, command palette, AI side chat)

## Current baseline (already on holographic branch — verify in UI, not by claim)

| Area | Present today | Gap vs Cursor |
|---|---|---|
| Editor theme | Cursor-inspired Monaco profile | Not Cursor’s full token set / product theme |
| CSV | Language map + Table/Raw toolbar | No spreadsheet editing, diffs, or large-file virtualization soak |
| Minimap | `scale: 1`, `renderCharacters: true` | Not full Cursor minimap behavior / slider / section headers |
| Tabs | Typed file badges | No preview tabs, pin, or dirty-state parity audit |
| Agent rail | Kairo / spoken-agent card | Not Cursor Chat / Composer / Agent panel |

## Workstreams

### P0 — Contract and honesty

1. Write ADR: “IDE stylistic alignment vs Cursor parity” (link ADR-008; state non-goals).  
2. Add a short checklist in `docs/UI_LAYOUT_LOCK.md` or IDE how-to: what operators may claim.  
3. Screenshot/receipt gate for any PR that says “Cursor-like.”

### P1 — Editor fidelity (console-web only)

1. Audit Monaco options vs Cursor defaults (word wrap, sticky scroll, bracket colorization,
   inlay hints, scrollbar, find widget). Land as `cursor-editor-theme` / options module.  
2. Minimap: user toggle + width; remove any remaining overlap with scrollbars (visual
   receipt).  
3. File-type pack: CSV (done path), JSON/YAML pretty+validate, Markdown preview policy,
   image tab behavior.  
4. Large-file policy: size threshold, disable minimap/table above N MB, show banner.

### P2 — Shell chrome (IDE mode)

1. Tab strip behaviors: dirty/pin/preview (product pick which three).  
2. Command palette parity **subset**: file open, symbol go-to, theme toggle — not full
   Cursor command surface.  
3. Split editor: one horizontal or vertical split MVP if ADR allows under ADR-008 lock.

### P3 — Agent surfaces (explicitly separate from Cursor Chat)

1. Keep Axon agent rail / dock as Axon product (Kairo, employees, briefing).  
2. Do **not** brand it as Cursor Chat. If AI panel layout inspiration is wanted, document
  as “layout inspiration” with different IA.

## Delivery slices (suggested PRs)

| Slice | Exit criteria |
|---|---|
| ADR + non-goals | Merged ADR; how-to updated |
| Monaco options audit | Diff of options table + vitest/contract for theme profile |
| Minimap/tabs polish | Visual receipts on IDE mode; Fast Gate green |
| File-type pack | CSV + one more type with tests |
| Split MVP (optional) | ADR amendment if layout lock blocks it |

## Verification

- Fast Gate on every slice  
- Manual IDE smoke: open TS + CSV Table/Raw + resize left agent card + minimap visible  
- No PR description may say “Cursor parity complete” until P0–P1 exit criteria are met
  and a product owner signs the non-goals list  

## Relationship to VAXON branches

Independent of `feat/vaxon-phase1-reliability` and `feat/parked-later-phase`. Do not block
or couple Cursor-plan work on wake-word / Android / soak.
