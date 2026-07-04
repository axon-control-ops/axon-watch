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
`docs/UI_LAYOUT_LOCK.md` and ADR-004 through ADR-007. Lane B may polish and bind
DTOs inside regions but must not rearrange the shell without coordinator approval
and a new ADR.

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
| KAIRO operator-presence integration (JX-1–JX-5) | Coordinator | Cross-cutting persona, voice, watch rules — planning only in `axon-local` |
| Cross-repo planning migration | Coordinator | `axon-local/Plans/Axon-Watch/` remains frozen planning home |
| Shared-contract field changes | Coordinator | `packages/shared-types`, run-state truth surfaces |

## Completed Queue

Work landed on `dev` (verified 2026-07-04):

| ID | Lane | Slice | Commit area |
|---|---|---|---|
| B1 | C (+ B) | Chat orchestration hook → superseded by C2 | `chat/orchestration.py` |
| B2 | B | Workspace catalog policy (doc) | `docs/WORKSPACE_CATALOG.md` |
| A1 | A | Bootstrap degraded signal clarity | watch summary copy |
| C1 | C (+ B) | Run history receipts in Active Run dock | `GET /api/runs/{id}/history` |
| D1 | D | Dev verify evidence + nightly gate | `npm run verify:evidence` |
| UX-4 | B | SSE live refresh + interruptive signals | `GET /api/live/events` |
| C2 | C (+ B) | Bounded command executor | `command_executor.py` |
| C3 | C (+ B) | Briefing **Notice/Advise** projection | `operator_briefing_rhythm.py` |
| B3 | B | Compact operator responsive CSS | `mockup-shell.css` `@media` |
| ADR-005 | B | Operator sidebar **Attention** toggle | `LeftSidebar`, `AttentionStackPanel` |
| ADR-006 | B | Command hero autosize + footer KAIRO CTA | `CommandSeamPanel`, `StatusBar` |
| ADR-007 p1 | B | Hide Monaco in Operator; IDE terminal collapse | `CenterWorkbench.vue` |
| **B7** | B | **Operator status/radar panel** (ADR-007 phase 2 option A) | `OperatorStatusRadarPanel.vue` |

## Active Queue (resume here)

One slice per pass; run the verification gate before the next item.

| Priority | ID | Lane | Slice | Status |
|---|---|---|---|---|
| **1** | **TEST-0** | All | Manual acceptance on `workspace_smoke`: Command executor, KAIRO Notice/Advise, Attention sidebar, status/radar panel, compact layout | **Ready** |
| 2 | C4 | C (+ B) | Wire **approve/reject** actions from Attention sidebar to existing API | Ready |
| 3 | C5 | C | Expand command executor (`git status`, resume-from-review command) | Ready |
| 4 | D2 | D | Capture `shell_boot_readiness` + latency timing evidence | Ready (PENDING in verify) |
| 5 | ADR-007 p3 | B | Terminal promotion OR read-only preview strip (deferred follow-up) | Ready after TEST-0 |

## Blocked / Coordinator-only

| ID | Lane | Slice |
|---|---|---|
| JX-1–5 | Coordinator | KAIRO watch rules, delivery policy, voice, persona, mobile |
| — | Coordinator | Cross-repo planning migration |
| — | Coordinator | `axon-local` ADR-005 (KAIRO presence layer) — **not** the same as repo ADR-005 (sidebar attention) |

## Layout ADR index (implementation repo)

| ADR | Topic |
|---|---|
| ADR-004 | Five-region shell grid (locked geometry) |
| ADR-005 | Operator sidebar Workspaces \| Attention toggle |
| ADR-006 | Command/KAIRO hero autosize + footer briefing CTA |
| ADR-007 | Operator workbench demotion — phase 1 editor hide, **phase 2 status/radar panel**, phase 3 TBD |

## Recently Landed (detail)

- approval thin slice (`requires_approval`, approve/reject)
- review-ready entry, completion, and resume-from-review
- workspace list API and DTO-bound Monaco hosts
- backend PTY terminal attachment (WebSocket, workspace-scoped)
- **zsh PTY via `ZDOTDIR`**
- file-backed Monaco editing + nested workspace explorer
- split mockup shell regions + resizable bottom terminal dock
- workspace-scoped chat thread rehydration
- **chat command dispatch** attach vs new run
- **bounded command executor (C2)** — health/list/read + execution receipts
- **briefing Notice/Advise (C3)** — canonical rhythm strings
- **SSE live refresh (UX-4)**
- **verify evidence tooling (D1)**
- **Operator layout (ADR-005/006)** — conversation-first right dock, Attention sidebar
- **Workbench demotion (ADR-007 p1)** — editor hidden in Operator
- **Operator status/radar panel (B7 / ADR-007 p2)** — fills upper workbench void with DTO-backed metrics + radar

## Assignment Rules

1. One slice, one lane, one verification gate.
2. No two agents edit the same file in the same pass.
3. Shared-contract changes require coordinator review before coding starts.
4. Every slice ends with:

```bash
npm run verify
python3 -m unittest discover -s tests
./scripts/dev/check-health.sh
```
