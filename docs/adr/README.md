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

## Verification

Use the template in `_TEMPLATE.md`, then run:

```bash
python3 scripts/verify/check_adr_governance.py
```

When a future slice starts generating real ADRs, CI can switch to:

```bash
python3 scripts/verify/check_adr_governance.py --strict-pending
```
