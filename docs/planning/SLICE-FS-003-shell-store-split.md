# SLICE FS-003 — Split `shell.ts` into bounded store slices

**Status:** In progress (2026-07-10)  
**Effective:** 2026-07-10  
**Owner:** `console-web`  
**Ratchet:** `apps/console-web/src/stores/shell.ts` — 3,775 lines max (target: `stores/shell/slices/*`)

## Problem

`apps/console-web/src/stores/shell.ts` remains the largest frontend hotspot and
still owns layout chrome, runtime probes, workspace file orchestration, run
state, chat state, and connector actions inside one setup store.

That monolith increases merge conflict risk and makes review harder, but the
console architecture still requires one authoritative Pinia store for shell
truth.

## Goal

Extract bounded factory slices under `apps/console-web/src/stores/shell/`
without changing the public `useShellStore()` import path or splitting shell
state across multiple Pinia stores.

**Exit criteria:**

- `shell.ts` drops below its active ratchet and keeps shrinking via same-patch
  extractions
- one Pinia store remains the state owner for all shell regions
- extracted slices accept refs/computeds/callbacks and return plain actions or
  computeds, matching the existing `createTerminalSessionStore` pattern
- callers keep importing from `apps/console-web/src/stores/shell`

## Non-goals

- Replacing the single-store shell architecture
- Reworking locked shell layout geometry from `docs/UI_LAYOUT_LOCK.md`
- Moving editor, KAIRO voice, run mutations, or thread orchestration in the
  first cut

## Constraints

- `docs/planning/UI_COMPOSITION_SPEC.md` requires all regions to read from one
  Pinia shell store; no hidden run or signal truth may live elsewhere.
- `docs/UI_LAYOUT_LOCK.md` keeps `shell.ts` as the shell state owner.
- Previous slice work already proved the safe pattern: helper factories under
  `apps/console-web/src/lib/` plus a thin setup-store facade.

## Target layout

```text
apps/console-web/src/stores/
  shell.ts
  shell-run-selection.ts
  shell/
    types.ts
    slices/
      create-dock-layout-slice.ts
      create-connectors-slice.ts
      create-runtime-probes-slice.ts
      create-runtime-summary-slice.ts
      create-operator-probes-slice.ts
      create-operator-briefing-slice.ts
      create-cursor-catalog-slice.ts
      create-operator-presence-settings-slice.ts
      create-inbox-signals-slice.ts
      create-catalog-loaders-slice.ts
      create-viewport-compact-slice.ts
      create-thread-surface-slice.ts
      create-ide-workbench-chrome-slice.ts
      create-composer-runtime-prefs-slice.ts
      create-operator-focus-slice.ts
      create-shell-display-slice.ts
```

## First-cut scope

### Step 1 — Extract store-owned types and helpers

Move exported shell-only types and local helpers to `stores/shell/types.ts`,
then re-export them from `stores/shell.ts` so existing imports keep working.

**Gate:** `npm run typecheck -w @axon-watch/console-web`

### Step 2 — Extract dock layout slice

Create `stores/shell/slices/create-dock-layout-slice.ts` for dock seam toggles,
left-sidebar mode, and dock hero mode actions. Keep the refs in `shell.ts`, but
move the actions into a factory that receives refs/computeds and returns the
public methods.

**Gate:** `npm run test -w @axon-watch/console-web`

### Step 3 — Extract connectors slice ✅

Move connector/tunnel/watch actions into `create-connectors-slice.ts`, injecting
runtime/briefing reload callbacks instead of importing the store.

**Gate:** `npm run verify:connector-parity`

### Step 4 — Extract runtime/operator probe loaders ✅

Move low-coupling probe loaders into factory slices:

- `create-runtime-probes-slice.ts` — `loadRuntimeStatus`, `loadRuntimeMcpTools`
- `create-operator-probes-slice.ts` — `loadOperatorFleetHealth`, `loadOperatorBrainGraph`

**Gate:** `npm run typecheck -w @axon-watch/console-web` + console-web vitest

### Step 5 — Extract briefing / summary / cursor catalog ✅

- `create-runtime-summary-slice.ts` — `loadRuntimeSummary`
- `create-operator-briefing-slice.ts` — `loadOperatorBriefing` (dock defaults + viewport via injected callbacks)
- `create-cursor-catalog-slice.ts` — `loadCursorCatalog` + model migration helper

**Gate:** `npm run typecheck -w @axon-watch/console-web` + console-web vitest

### Step 6 — Extract operator presence + inbox signal slices ✅

- `create-operator-presence-settings-slice.ts` — operator presence load/save/reset + settings surface toggles
- `create-inbox-signals-slice.ts` — `loadInbox`, CLEAR, verify-dismiss, and linked handoff dismissal

**Gate:** `python3 scripts/guardrails/check_file_sizes.py` + `npx vitest run src/lib/signal-handoff-dismiss.test.ts`

**Result:** `shell.ts` ratcheted from `4419` to `4278`.

### Step 7 — Extract catalog loaders ✅

- `create-catalog-loaders-slice.ts` — `loadWorkspaces`, `loadRuns`, `loadRunHistory`, `syncCurrentWorkspace`, and auto-sync helper

Keep `setCurrentWorkspace` in `shell.ts` (editor/thread/terminal side effects).

**Gate:** `python3 scripts/guardrails/check_file_sizes.py` + workspace catalog vitest

**Result:** `shell.ts` ratcheted from `4278` to `4206`.

### Step 8 — Extract six low-risk factory slices ✅

- `create-viewport-compact-slice.ts` — `mobileCompactLayout`, resize bind/unbind, owns
  `lastViewportCompactRequested` and exports get/set for briefing wiring
- `create-thread-surface-slice.ts` — surface helpers + workspace surface thread id map
- `create-ide-workbench-chrome-slice.ts` — terminal reveal/toggle, activity view,
  explorer/agent dock toggles (still feeds `createTerminalSessionStore`)
- `create-composer-runtime-prefs-slice.ts` — runtime target/model prefs + picker
  visibility (keeps `createCursorCatalogSlice` separate)
- `create-operator-focus-slice.ts` — attention/briefing/mission/command focus chrome
- `create-shell-display-slice.ts` — read-only display/capability computeds (excludes
  editor docs, Kairo voice, composer submit/queue)

**Gate:** `python3 scripts/guardrails/check_file_sizes.py` + signal-handoff + workspace catalog vitest

**Result:** `shell.ts` ratcheted from `4206` to `3775`.

### Next candidate

- Editor document/session helpers, or IDE thread tab orchestration (higher coupling)

## Verification checklist

```bash
cd /home/edp/axon-nvme/repos/axon-watch
python3 scripts/guardrails/check_file_sizes.py
npm run typecheck -w @axon-watch/console-web
npm run test -w @axon-watch/console-web
npm run verify:contracts
```

## Rollback

Revert the FS-003 slice commit. `shell.ts` stays the compatibility facade, so
consumers do not need import-path changes.

## Lock rules

1. Keep one Pinia store; use factory slices only.
2. Slices must not import `useShellStore()` or create circular dependencies.
3. Lower `hotspot_budgets.json` in the same patch once the extracted file count
   creates enough headroom to ratchet downward.
