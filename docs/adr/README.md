# ADR Process

This directory holds Axon-Watch architecture decision records.

The process follows the frozen planning governance:

1. Create new ADRs with sequential numbering like `ADR-001-topic.md`.
2. Start in `Proposed` while the decision is open.
3. Move to `Accepted` when the decision becomes project source of truth.
4. If the decision changes later, create a new ADR and mark the old one
   `Superseded`.

## Immutability Rule

Accepted ADRs are immutable decision records.

Allowed edits after acceptance:

- typo fixes
- formatting fixes
- metadata clarification that does not change the decision
- links to the superseding ADR

Disallowed edits after acceptance:

- changing the decision itself
- materially changing trade-off analysis
- swapping the chosen alternative without creating a new ADR

## Required Sections

Every numbered ADR must include:

- `Status`
- `Context`
- `Decision`
- `Alternatives Considered`
- `Trade-Offs`
- `Consequences`
- `Reevaluation Triggers`

## Accepted ADRs

- [ADR-001: Vue 3, Pinia, Monaco, and xterm.js stack](ADR-001-vue-monaco-xterm-stack.md)
- [ADR-002: Control-plane run truth and backend-only briefing](ADR-002-control-plane-run-truth-and-briefing-seam.md) — superseded for shell briefing by ADR-003
- [ADR-003: Shell consumes operator briefing in the right dock](ADR-003-shell-consumes-operator-briefing.md)
- [ADR-004: Locked console shell layout](ADR-004-locked-console-shell-layout.md) — operator right-dock seam order superseded in part by ADR-005
- [ADR-005: Operator sidebar attention toggle](ADR-005-operator-sidebar-attention-toggle.md)
- [ADR-006: Operator command hero and footer attention](ADR-006-operator-command-hero-and-footer-attention.md)
- [ADR-007: Operator workbench demotion](ADR-007-operator-workbench-demotion.md)
- [ADR-008: IDE shell content lock](ADR-008-ide-shell-content-lock.md)

**Planning-only (not yet copied here):**

- ADR-005 KAIRO as operator presence layer — accepted in
  `axon-local/Plans/Axon-Watch/ADR-005-kairo-as-operator-presence-layer.md`.
  Implementation blocked until coordinator assigns the JX slices.

Use the template in `_TEMPLATE.md`, then run:

```bash
python3 scripts/verify/check_adr_governance.py
```

When a future slice starts generating real ADRs, CI can switch to:

```bash
python3 scripts/verify/check_adr_governance.py --strict-pending
```
