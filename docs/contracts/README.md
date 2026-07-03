# Contract Baseline

This repo now owns its first real shared contract package at
`packages/shared-types/`.

## Source Of Truth

- Frozen planning semantics still come from `axon-local/Plans/Axon-Watch/`.
- Code ownership for the executable DTO baseline now lives in
  `packages/shared-types/`.

## Scope Of This Slice

This correction pass replaces the console shell's `unknown` placeholders with
real canonical shared types for:

- `RunRecord`
- `ApprovalRecord`
- `WorkspaceRecord`
- `RuntimeSummary`
- `InboxItem`
- `SignalView`
- `SignalEvent`
- `ThreadMessage`
- `WatchSummary`

The control-plane now assembles `RuntimeSummary` live in
`services/control-plane/app/runtime_summary_assembler.py` while keeping the
payload shape canonical and boot-safe.

Representative JSON fixtures live in `packages/shared-types/fixtures/`.

Verify the shared contract package from the repo root:

```bash
npm run verify:shared-types
npm run verify:contracts
```

## Additive-First Rule

This slice only encodes fields explicitly grounded in the frozen planning
bundle, plus the minimum nullability needed for baseline runtime fixtures.

If a future slice needs richer field-level semantics for approvals, workspaces,
threads, or watch payload internals, that work must stay additive-first unless a
planning amendment is approved.
