# Workspace Catalog Policy

**Status:** Documented deferral — 2026-07-04  
**Owner:** Lane B (presentation) + Lane C (API catalog)

## Problem

The control-plane workspace API exposes the full catalog (including IDs such as
`workspace_alpha` used in tests and bootstrap seeds). The operator shell sidebar
shows a **trimmed mockup catalog** of seven workspace IDs for presentation parity.

This is intentional, not drift.

## Shell authority (presentation)

`apps/console-web/src/lib/mockup-shell-view.ts`:

- `MOCKUP_WORKSPACE_IDS` — visible sidebar set
- `mergeMockupWorkspaceCatalog()` — merges API records into the mockup order
- `resolveBootstrapWorkspaceId()` — picks active run workspace when sidebar-visible,
  else `workspace_smoke`, else first mockup entry

The shell **must not** invent workspace semantics beyond this filter. Hidden API IDs
remain reachable for tests, handoffs, and future catalog expansion.

## API authority (truth)

`GET /api/workspaces` returns all registered workspaces from
`services/control-plane/app/workspace_catalog.py`.

Contract tests and chat/run tests may use `workspace_alpha` and other non-mockup IDs.

## Rules

1. Do not remove API catalog entries solely to match the sidebar without a coordinator
   contract amendment.
2. Do not add sidebar workspaces that are absent from `MOCKUP_WORKSPACE_IDS` without
   updating the mockup list and handbook.
3. Bootstrap selection must stay deterministic via `resolveBootstrapWorkspaceId()`.
4. Unification of API catalog and sidebar IDs is a **future slice** — not required for
   Lane B shell parity while this document stands.

## Verification

- `mockup-shell-view.test.ts` — catalog merge and bootstrap selection
- Manual: sidebar shows seven workspaces; API `/api/workspaces` may return more

## Related

- `docs/HOW-TO-HANDBOOK.md` → boot limitations
- `docs/MULTITASK-LANES.md` → active queue item B3 (documented)
