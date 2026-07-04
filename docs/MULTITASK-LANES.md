# Axon-X Post-Stabilization Multi-Agent Lanes

This map defines non-overlapping ownership after the stabilization pass.
Use it before resuming parallel agent work.

## Serial-Only Truth (Coordinator Lane)

One lane owns semantic truth. No other lane may edit these without coordinator
approval:

- `axon-local/Plans/Axon-Watch/run-state.md`
- `packages/shared-types/src/run.ts`
- `packages/shared-types/src/runtime.ts`
- `packages/shared-types/src/briefing.ts`
- `packages/shared-types/src/signals.ts`
- `services/control-plane/app/domain/run_state.py`
- `services/control-plane/app/domain/run_transitions.py`
- `docs/contracts/run-state-stop-resume-amendment-request.md`

Coordinator responsibilities:

- approve or reject planning amendments
- resolve contract drift before merge
- assign slices with explicit file ownership
- block parallel edits that touch the same truth surface

## Safe Parallel Lanes

### Lane A — Watch Depth

Ownership:

- `services/axon-watch/app/signals/*`
- `services/axon-watch/app/main.py` (watch routes only)
- watch-specific tests under `tests/test_watch_*`

May:

- add signal producers and ranking metadata
- extend watch inbox payloads additively

Must not:

- change run-state semantics
- change shared DTO fields without coordinator approval

### Lane B — Console Shell Surfaces

Ownership:

- `apps/console-web/src/**`
- console-web styles and partial shell layout

**Layout lock:** region geometry and dock seam order are frozen — see
`docs/UI_LAYOUT_LOCK.md` and ADR-004. Lane B may polish and bind DTOs inside
regions but must not rearrange the shell without coordinator approval and a new ADR.

May:

- build editor, terminal, preview, and dock surfaces
- consume existing control-plane APIs

Must not:

- invent run phases or approval semantics locally
- add briefing mutation controls inside the display-only briefing panel

### Lane C — Control-Plane Product Behavior

Ownership:

- `services/control-plane/app/runs/*`
- `services/control-plane/app/persistence/*`
- `services/control-plane/app/main.py` (run/briefing routes)
- control-plane tests

May:

- deepen stop/resume/review flows within frozen transitions
- extend SQLite persistence and history receipts

Must not:

- bypass approval boundary through generic resume
- add transitions without contract amendment

### Lane D — Dev Runtime And Verification

Ownership:

- `scripts/dev/**`
- root `package.json` verify scripts
- `docs/HOW-TO-HANDBOOK.md`
- `README.md`

May:

- improve startup supervision, health probes, and verify entrypoints

Must not:

- change product semantics while touching tooling

## Blocked Until Explicit Assignment

Do not start these until coordinator opens the slice:

| Item | Owner | Reason |
|---|---|---|
| KAIRO operator-presence integration (ADR-005, JX-1–JX-5) | Coordinator | Cross-cutting persona, voice, watch rules — planning only in `axon-local` |
| Cross-repo planning migration | Coordinator | `axon-local/Plans/Axon-Watch/` remains frozen planning home |
| Fitness timing gates | Lane D | `shell_boot_readiness`, latency budgets — PENDING in verify |
| Shared-contract field changes | Coordinator | `packages/shared-types`, run-state truth surfaces |

## Active Queue (resume here)

Work in order. One slice per pass; run the verification gate before the next item.

| # | Lane | Slice | Status |
|---|---|---|---|
| **B1** | C (+ B surface) | Chat orchestration hook — agent reply + `review_ready` after dispatch | **done** |
| **B2** | B | Workspace catalog policy (doc-only) | **done** — `docs/WORKSPACE_CATALOG.md` |
| **A1** | A | Watch signal depth / degraded bootstrap clarity | **done** |
| **C1** | C (+ B surface) | Run history receipts visible in dock | **done** |
| **D1** | D | Dev verify / health polish (non-semantics) | **done** |
| **UX-4** | B | SSE live update polish (seam refresh + interruptive signals) | **done** |

## Next Queue (pick from here)

| Priority | ID | Lane | Slice | Blocked? |
|---|---|---|---|---|
| **1** | **C2** | C (+ B transcript) | **Bounded command executor** — run real workspace actions from chat (health probe, file read, dir list); agent messages include evidence; then `review_ready` | **Ready** |
| 2 | C3 | C | Briefing **Notice/Advise** depth from canonical run/signal state (JX-3 thin slice) | Ready |
| 3 | B3 | B | Responsive **compact operator** layout (CSS only, no voice — not full mobile JX-4) | Ready |
| — | JX-1–5 | Coordinator | KAIRO presence (watch rules, delivery, voice, persona, mobile) | **Blocked** |
| — | — | Coordinator | Cross-repo planning migration | **Blocked** |

**Recommendation:** start **C2** — it is the direct successor to B1 stub orchestration and delivers operator-visible “real” execution without LLM or coordinator unlock.

### C2 scope sketch (for assignment)

- NEW `services/control-plane/app/chat/command_executor.py` — classify + run bounded actions
- Extend `orchestration.py` to call executor while run is `executing`, append agent message with stdout snippet
- Persist execution receipt on run history before `review_ready`
- Tests: executor unit tests + chat integration test with mocked workspace root
- Must not: add LLM, change run-state transitions, bypass approvals

### Parallel helper prompt (after C2 starts)

Lane B companion slice: show executor output in Conversation seam with monospace block styling (read-only).

Parallel rule: **B1 must finish before A1/C1** if they touch `chat/service.py` or
run orchestration in the same pass. Lane A and D may run in parallel with B2 only.

## Suggested Next Slices

Superseded by **Active Queue** above. After B1 lands:

1. **Lane A** — watch summary degraded signal clarity in bootstrap dev mode
2. **Lane C** — run history receipts visible in dock (within frozen transitions)
3. **Lane D** — dev verify / health polish (D1)

## Recently Landed

- approval thin slice (`requires_approval`, approve/reject)
- review-ready entry, completion, and resume-from-review
- workspace list API and DTO-bound Monaco hosts
- startup supervision reliability slice
- backend PTY terminal attachment (WebSocket, workspace-scoped)
- **zsh PTY invocation via `ZDOTDIR`** (fixes bash-only `--rcfile` bug; verified 2026-07-04)
- terminal scrollback persistence, client-side clear, DOM paste handler
- richer inbox ranking (severity, recency, unresolved duration, status,
  action-type, workspace priority)
- file-backed Monaco editing (workspace README.md / notes.txt with Save)
- shell consumption of `/api/briefing` in the right dock
- nested workspace explorer tree with lazy file loading
- nested workspace file creation and active-file rename
- split mockup shell regions (`TopBar`, `LeftSidebar`, `CenterWorkbench`,
  `RightDock`, `StatusBar`) with a resizable bottom terminal dock
- workspace-scoped chat thread rehydration on boot/workspace select
  (`GET /api/workspaces/{workspace_id}/chat/thread` + history read)
- **chat command dispatch** attach vs new run (`POST /api/chat/messages` +
  `refreshRunSurfaces` on submit)
- **operator-facing dock seam titles** via `dock-seam-layout.ts`
- **UX-4 live update polish** — `GET /api/live/events` SSE refresh hints, `live-events-session.ts`, interruptive signal seam promotion, reduced-motion overrides
- **silent empty thread lookup** (HTTP 200 + `thread_id: null`)
- **bootstrap workspace catalog trim** (`mergeMockupWorkspaceCatalog`, `workspace_smoke` default)
- **chat orchestration hook** — agent transcript reply + dispatch → `review_ready` (`chat/orchestration.py`)
- **workspace catalog policy** documented in `docs/WORKSPACE_CATALOG.md`
- **run history receipts** — `GET /api/runs/{run_id}/history` + Active Run dock list
- **bootstrap degraded signal clarity** — Lane A1 copy/metadata (`c464984`)
- **SSE live refresh** — `GET /api/live/events` + `live-events-session.ts` (UX-4)
- **verify evidence tooling** — `npm run verify:evidence`, `npm run verify:nightly` (D1)
- lower default terminal dock height (~240px fresh session, 280px cap)

## Assignment Rules

1. One slice, one lane, one verification gate.
2. No two agents edit the same file in the same pass.
3. Shared-contract changes require coordinator review before coding starts.
4. Every slice ends with the stabilization verification gate:

```bash
python3 -m py_compile services/control-plane/app/main.py services/control-plane/app/runs/service.py services/control-plane/app/domain/run_state.py services/control-plane/app/domain/run_transitions.py services/control-plane/app/operator_briefing.py
npm run build -w @axon-watch/console-web
npm run verify
python3 -m unittest discover -s tests
./scripts/dev/down.sh
./scripts/dev/up.sh
./scripts/dev/check-health.sh
```
