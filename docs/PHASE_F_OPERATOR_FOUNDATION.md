# Phase F — Operator Foundation II

**Opened:** 2026-07-05  
**Precondition:** `docs/INITIAL_PROGRESS_CLOSEOUT.md`  
**Primary operator URL:** http://127.0.0.1:4173  
**Fallback URL:** http://127.0.0.1:7734

## Purpose

Phase F is the locked follow-on build after Initial Progress.

It exists to make Axon-X a durable daily-driver operator surface by adding:

- runtime fabric (Cursor + Codex, local + cloud)
- dedicated `/vault` surface
- dedicated `/data` surface
- finished DashPro monitor signals
- final shell polish

It does **not** reorder or replace the cutover or parity records. Those remain
historical truth.

## Design references

This phase is grounded in verified public guidance:

- [Cursor CLI](https://cursor.com/docs/cli/overview)
- [Cursor Hooks](https://cursor.com/docs/hooks)
- [OpenAI Codex CLI](https://developers.openai.com/codex/cli)
- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents.md)
- [OpenAI evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents?lang=en-US)
- [Anthropic: Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/index)

## Lock rule

1. Execute slices in the locked order below unless the operator reprioritizes explicitly.
2. One slice per pass; run the slice gate before starting the next.
3. Do not claim runtime parity, vault parity, or full retirement until the
   relevant slice gate is green.
4. New discoveries go into the append log; they do not silently reshuffle the order.
5. Runtime policy belongs in explicit code/config, not hidden in prompts.

## Architecture direction

- Axon-X owns orchestration, approvals, state, and receipts.
- Cursor is the primary live interactive runtime.
- Codex is the primary scripted / automation runtime.
- Local and cloud runtimes both belong in the same explicit runtime fabric.
- MCP is the native-tools integration layer.
- Continuous improvement uses traces, evals, and operator review.

## Current state (2026-07-06)

| Area | Status |
|---|---|
| Initial Progress | **Complete** |
| Runtime fabric (F1) | **Verified / gate green** |
| Dedicated vault route (F2 thin) | **Verified / gate green** — not full vault parity |
| Dedicated data route (F3) | **Verified / gate green** |
| DashPro monitors (F4) | **Verified / gate green** |
| Shell polish (F5) | **Verified / gate green** |
| Full vault parity (Vault II) | **Phase G — G1** (`docs/PHASE_G_SIGNAL_PARITY.md`) |
| Full axon-local retirement (F6) | **Deferred to Phase G — G6** |

**Next locked phase:** `docs/PHASE_G_SIGNAL_PARITY.md`

## Locked order

### F0 — Closeout and governance sync

- [x] **F0.1** Publish `docs/INITIAL_PROGRESS_CLOSEOUT.md`
- [x] **F0.2** Publish this checklist
- [x] **F0.3** Mark `docs/TRANSITION_PHASE_E_TODO.md` as Initial-Progressed
- [x] **F0.4** Update roadmap / import matrix / lanes docs
- [x] **F0.5** Reclassify temporary local-model Lane B as an interim checkpoint,
  not the Phase F target
- [x] **F0.6** Sync planning mirror to axon-local

**Exit gate:** docs updated, mirror synced, build source-of-truth aligned.

### F1 — Runtime fabric

- [x] **F1.1** Add `services/control-plane/app/cli_runtime/` bounded package
- [x] **F1.2** Runtime catalog: discover Cursor/Codex local binaries and auth posture
- [x] **F1.3** Runtime router: Cursor local, Codex local, Cursor cloud, Codex cloud
- [x] **F1.4** Replace temporary local-model Lane B path with runtime-backed IDE composer
- [x] **F1.5** Add runtime status API and transcript/event normalization
- [x] **F1.6** Add gate script + focused tests

**Exit gate:** `npm run verify:cli-runtime`

### F2 — Dedicated vault route

- [x] **F2.1** Add dedicated `/vault` route reachable from Operator and IDE
- [x] **F2.2** Add control-plane vault status/import APIs
- [x] **F2.3** Show import posture, available key names, and consumer map
- [x] **F2.4** Link skipped monitor/config states back to `/vault`
- [x] **F2.5** Add gate script + focused tests

**Exit gate:** `npm run verify:vault-surface`

### F3 — Dedicated data route

- [x] **F3.1** Add dedicated `/data` route reachable from Operator and IDE
- [x] **F3.2** Add read-only control-plane/watch table APIs
- [x] **F3.3** Show persisted runs, chat, handoffs, commands, events, receipts, suppressions
- [x] **F3.4** Add diagnostic export path
- [x] **F3.5** Add gate script + focused tests

**Exit gate:** `npm run verify:operator-data`

### F4 — DashPro monitor signals

- [x] **F4.1** Finish Sentry/PostHog monitor checks against vault-fed credentials
- [x] **F4.2** Project warning/critical checks into watch inbox + operator UI
- [x] **F4.3** Add clear operator copy for skipped / missing-credential states
- [x] **F4.4** Add child-project monitor verification

**Exit gate:** `npm run verify:dashpro-monitors`

### F5 — Final polish closure

- [x] **F5.1** Finish Mission Control scroll and internal overflow polish
- [x] **F5.2** Finish IDE chrome so it is distinct from operator mode
- [x] **F5.3** Bind runtime status cleanly into the agent dock
- [x] **F5.4** Resolve explorer / loading-state rough edges
- [x] **F5.5** Run production shell regression

**Exit gate:** `npm run verify:production-operator`

### F6 — Retirement readiness review

- [ ] **F6.1** Reassess `blockers_for_full_retirement`
- [ ] **F6.2** Decide whether E6 can resume
- [ ] **F6.3** Create `test12-full-retirement-readiness.sh` only if all prior gates are green

**Exit gate:** explicit operator sign-off only

## Per-slice workflow

1. Bounded module first; no monolith growth
2. Add or amend a doc/spec when behavior is non-trivial
3. Add the cheapest reliable verification in the same slice
4. Keep runtime policy explicit and observable
5. Append log entry; do not rewrite history

## Append log

### 2026-07-05 — Phase F opened

- Initial Progress closed as complete.
- Official runtime guidance favors Axon-X-owned orchestration with explicit
  Cursor/Codex local + cloud runtime workers.
- `/vault` and `/data` are first-class product surfaces in this phase.
- Full axon-local retirement remains deferred.

### 2026-07-06 — Phase F complete; Phase G opened

- F0–F5 slices and gates complete.
- F6 retirement review moved to Phase G G6 with G1–G5 preconditions.
- Vault II (full Signal crypto parity) is G1 in `docs/PHASE_G_SIGNAL_PARITY.md`.
- ReAct monolith is not the target; runtime fabric + persisted run truth is.
