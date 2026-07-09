# SLICE FS-001 — Split `control-plane.ts` API client

**Status:** Complete (2026-07-09)  
**Effective:** 2026-07-09  
**Owner:** `console-web`  
**Ratchet:** `apps/console-web/src/api/control-plane.ts` — 12 lines (re-export facade; was 1,399)

## Problem

`apps/console-web/src/api/control-plane.ts` is a single module that owns every
control-plane HTTP call, DTO shim, and blob download helper. At 1,399 lines it is
the largest TypeScript hotspot after `shell.ts` and blocks clean domain
ownership in the frontend.

Every new API surface (KAIRO, vault, runs, chat) increases merge conflict risk
and makes tree-shaking and targeted testing harder.

## Goal

Split the client into bounded domain modules under `apps/console-web/src/api/`
while keeping `control-plane.ts` as a thin compatibility re-export facade.

**Exit criteria:**

- `control-plane.ts` ≤ 120 lines (re-exports + `LEGACY_AXON_LOCAL_FALLBACK_URL` only)
- Each new `*-api.ts` module ≤ 350 lines (soft target)
- `hotspot_budgets.json` ratchet for `control-plane.ts` lowered to the new size
- No import churn for existing callers (`from '../api/control-plane'` keeps working)

## Non-goals

- Changing API routes or DTO shapes on the server
- Splitting `shell.ts` or CSS monoliths (separate slices FS-002+)
- Moving types out of `contracts/canonical` (reuse existing shared types)

## Target layout

```text
apps/console-web/src/api/
  client.ts              # controlPlaneBaseUrl(), json fetch helpers, blob helpers
  runtime-api.ts         # /api/runtime/*, /api/readiness, /api/health
  vault-api.ts           # /api/vault/*
  data-api.ts            # /api/data/*
  inbox-api.ts           # /api/inbox/*
  operator-api.ts        # /api/briefing, /api/operator/*, presence settings
  runs-api.ts            # /api/runs/*
  workspace-api.ts       # /api/workspaces/*, files, handoffs, terminal sessions
  chat-api.ts            # /api/chat/*, resolveChatAttachmentUrl
  # kairo-api.ts intentionally deferred — KAIRO clients remain in lib/kairo-*-client.ts
  connectors-api.ts      # /api/connectors, /api/tunnel/*, /api/watch/*
  live-events-api.ts     # /api/live/events (if not folded into operator-api)
  control-plane.ts       # re-export * from above + LEGACY_AXON_LOCAL_FALLBACK_URL
```

## Domain map (current exports → target module)

| Target module | Functions / types to move |
|---------------|----------------------------|
| `client.ts` | `controlPlaneBaseUrl`, shared `fetchJson`, `fetchBlob`, error wrapper |
| `runtime-api.ts` | `fetchRuntimeSummary`, `fetchRuntimeStatus`, `fetchRuntimeMcpTools`, cursor/codex auth, `fetchReadiness`, runtime DTO interfaces |
| `vault-api.ts` | All `fetchVault*`, `setupVault`, import/export CSV/backup |
| `data-api.ts` | `fetchDataSnapshot`, `downloadDataExport` |
| `inbox-api.ts` | `fetchInbox`, `acknowledgeInboxSignals` |
| `operator-api.ts` | `fetchOperatorBriefing`, fleet/brain graph, presence settings |
| `runs-api.ts` | `fetchRuns`, `fetchRun`, history, create/complete/stop/resume/approve/reject |
| `workspace-api.ts` | workspaces list/detail, files CRUD, handoffs, terminal sessions |
| `chat-api.ts` | `postChatMessage`, threads, history, attachments, `resolveChatAttachmentUrl` |
| *(deferred)* `kairo-api.ts` | Still in `lib/kairo-*-client.ts` — not part of this facade split |
| `connectors-api.ts` | connectors, tunnel, watch commands |

## Implementation steps

### Step 1 — Shared client helpers (no caller changes) ✅

1. Create `client.ts` with `controlPlaneBaseUrl()`, `apiUrl(path)`, `fetchJson<T>()`, `fetchBlob()`.
2. Move helper privately first; keep exports in `control-plane.ts` unchanged.

**Gate:** `npm run typecheck -w @axon-watch/console-web`

### Step 2 — Extract leaf modules (vault, data, inbox) ✅

1. Move vault functions + vault-specific interfaces to `vault-api.ts`.
2. Move data and inbox similarly.
3. Re-export from `control-plane.ts`.

**Gate:** `npm run test -w @axon-watch/console-web`

### Step 3 — Extract runtime + runs + workspace ✅

1. `runtime-api.ts` and `runs-api.ts` — highest call volume; verify runtime picker still loads.
2. `workspace-api.ts` — files, terminal, handoffs.

**Gate:** `npm run verify:cli-runtime` (runtime auth surfaces)

### Step 4 — Extract chat + operator + connectors ✅

1. `chat-api.ts` — includes attachment URL resolver used by conversation seam.
2. `operator-api.ts` — briefing, fleet, brain graph, presence settings.
3. `connectors-api.ts` — tunnel + watch command panel.

**Gate:** `npm run verify:agent-dock-parity` + `npm run verify:voice-cockpit`

### Step 5 — Thin facade + ratchet ✅

1. Replace `control-plane.ts` body with re-exports only.
2. Lower `hotspot_budgets.json` `max_lines` for `control-plane.ts` to 12.
3. Domain modules remain bounded under soft limit except none exceed hard limit.

**Gate:** `python3 scripts/guardrails/check_file_sizes.py` passes

## Verification checklist

```bash
cd /home/edp/axon-nvme/repos/axon-watch
python3 scripts/guardrails/check_file_sizes.py
npm run typecheck -w @axon-watch/console-web
npm run test -w @axon-watch/console-web
npm run verify:contracts
npm run verify:agent-dock-parity
```

Manual smoke on `:4173`:

- Runtime status panel loads (runtime-api)
- Vault unlock/import (vault-api)
- IDE chat send + attachment preview (chat-api)
- KAIRO converse health reply (`lib/kairo-converse-client.ts`)

## Rollback

Revert the slice in one commit. `control-plane.ts` as a single file is the
compatibility fallback; no server changes required.

## Follow-on slices

| Slice | Target | Priority |
|-------|--------|----------|
| FS-002 | `services/control-plane/app/main.py` → `routes/*` | P0 |
| FS-003 | `shell.ts` → domain Pinia stores | P0 |
| FS-004 | `ide-layout.css` + `mockup-shell.css` feature split | P0 |
| FS-005 | `AgentDockComposer.vue` subcomponents | P1 |

## Lock rules

1. One domain module per PR sub-step when possible (easier review).
2. Same-patch ratchet: any extraction must lower `max_lines` for the source file.
3. No new logic in `control-plane.ts` after Step 5 — add to the appropriate `*-api.ts`.
