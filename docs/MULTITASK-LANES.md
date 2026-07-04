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

Do not start these in parallel until coordinator opens the slice:

- KAIRO operator-presence integration (planning exists in axon-local only)
- cross-repo planning moves out of `axon-local/Plans/Axon-Watch/`

**Recently landed (no longer blocked):**

- approval thin slice (`requires_approval`, approve/reject)
- review-ready entry, completion, and resume-from-review
- workspace list API and DTO-bound Monaco hosts
- startup supervision reliability slice
- backend PTY terminal attachment (WebSocket, workspace-scoped)
- richer inbox ranking (severity, recency, unresolved duration, status,
  action-type, workspace priority)
- file-backed Monaco editing (workspace README.md / notes.txt with Save)
- shell consumption of `/api/briefing` in the right dock
- nested workspace explorer tree with lazy file loading
- richer briefing panel (`top_signals`, connectivity)

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

## Suggested Next Slices

After the current thin slices (updated 2026-07-04):

1. **Lane B** — nested file creation / rename beyond read-write-open
2. **Coordinator** — KAIRO operator-presence integration when explicitly assigned
