# SLICE FS-003 — Split `shell.ts` into bounded store slices

**Status:** In progress (2026-07-10)  
**Effective:** 2026-07-10  
**Owner:** `console-web`  
**Ratchet:** `apps/console-web/src/stores/shell.ts` — 4,534 lines max (target: `stores/shell/slices/*`)

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
      # follow-ons:
      # create-operator-probes-slice.ts
      # create-runtime-probes-slice.ts
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
