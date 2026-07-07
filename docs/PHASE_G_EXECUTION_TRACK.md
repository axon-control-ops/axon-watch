# Phase G Execution Track — Axon-X → axon-local Retirement

**Opened:** 2026-07-06  
**Primary operator URL:** http://127.0.0.1:4173  
**Fallback (explicit only):** http://127.0.0.1:7734  

## Purpose

Single followable checklist tying **Phase G orchestration**, **Full Access agent execution**, **UX-IDE / JARVIS**, and **G4–G6 retirement** into one ordered track.

Parent checklist: `docs/PHASE_G_SIGNAL_PARITY.md`  
IDE refocus: `.cursor/plans/axon-x_ide_mode_refocus_ee008b8e.plan.md`  
KAIRO: `docs/planning/KAIRO_MODE.md`

## Lock rule

1. Execute waves in order unless the operator reprioritizes explicitly.
2. One bounded slice per pass; run the slice gate before starting the next.
3. Do not rewrite Phase G — amend this track and append to `PHASE_G_SIGNAL_PARITY.md`.

---

## Wave 1 — Unblock real Axon-X development (START HERE)

| # | Slice | Deliverable | Gate | Status |
|---|---|---|---|---|
| 1 | **G3.4-complete** | IDE Stop → `stop_run` → `process_registry`; resume/cancel tests | `tests/test_cli_runtime_process_registry.py` | **Done** |
| 2 | **G3.8 Full Access UI** | Composer toggle; consent-as-approval; executing tier; stream-json blocks | Chat + dispatch + CLI tests | **Done** |
| 3 | **G3.1 contract** | `docs/planning/agent-orchestration-contract.md` | Doc review | Done |
| 4 | Operator/IDE threads | Separate operator vs IDE conversation threads | Chat surface tests | Done |

**Wave 1 exit:** Agent Full Access works on `axon-watch` / DashPro workspaces without `:7734` for agent turns.

---

## Wave 2 — Close G3 orchestration gate

| # | Slice | Deliverable | Gate | Status |
|---|---|---|---|---|
| 5 | **G3.5** | MCP tools in dispatch metadata; composer Tools panel from registry | `/api/runtime/mcp-tools` + dispatch test | **Done** |
| 6 | **G3.6** | Donor workflow parity tests (bounded `IMPORT_MATRIX` set) | `tests/test_agent_orchestration_parity.py` | **Done** |
| 7 | **G3.7** | `verify:agent-orchestration-parity` fully green | `test20-agent-orchestration-parity.sh` | **Done** |

**Wave 2 exit:** `LEGACY_CONNECTOR_INVENTORY` item 1 (ReAct loop) marked **replaced**.

---

## Wave 3 — UX + JARVIS (parallel; does not block G4)

| # | Slice | Deliverable | Source |
|---|---|---|---|
| 8 | **UX-IDE-1** | Quiet IDE: chip not radar; no watch in status bar (healthy) | IDE refocus plan | **Done** |
| 9 | **UX-IDE-2** | `IdeInterruptPanel` (approvals + critical signals) | IDE refocus + G3.3 | **Done** |
| 10 | **KAIRO Ask** | Ask mode + KAIRO persona prompt | JARVIS video personality | **Done** |
| 11 | **UX-IDE-3** | Research cards in agent transcript | JARVIS video |
| 12 | **UX-IDE-4** | `@selection`, `@terminal` context tokens | JARVIS “pull up notes” |
| 13 | **UX-IDE-5** | Opt-in IDE voice strip | JARVIS hands-free (later) |

---

## Wave 4 — Retirement path (G4 → G6)

| # | Slice | Deliverable | Blocks |
|---|---|---|---|
| 14 | **G4.1** | Connector inventory with probe + removal criteria | — |
| 15 | **G4.2–G4.5** | WhatsApp / tunnel / voice / dock parity (or explicit discard) | DashPro `:7734` fallback |
| 16 | **G4.6** | `verify:connector-parity` | — |
| 17 | **G5** | Capability matrix + extended regression | — |
| 18 | **G6** | One week `:4173` only + operator sign-off | **Retirement** |

---

## Full Access operator flow (G3.8)

```text
1. IDE → Agent → Full Access ON (session consent)
2. Submit prompt → run created → executing immediately (no per-run Approve)
3. Cursor CLI stream-json → thinking / tool / edit blocks in IDE transcript
4. Successful turn → run auto-completes (failed → review_ready in Mission Control)
5. IDE thread stays separate from operator command thread
```

| Tier | Cursor | Codex | When |
|---|---|---|---|
| Consultative | `--mode plan` | read-only sandbox | Ask, Plan, Agent (default) |
| Full Access | default agent (no `--mode`) | workspace-write | Agent + session Full Access consent |

Env fallback: `AXON_WATCH_AGENT_TOOL_EXECUTION=1` (same gate as composer Full Access).

**Next up (Wave 3):** **UX-IDE-3** research cards in agent transcript, or Wave 4 **G4.1** connector inventory.

---

## What still forces `:7734`

1. Agent loop with file edits → Wave 1–2  
2. Child-project connectors (WhatsApp, tunnel) → G4  
3. Voice / mobile cockpit → G4.4 or explicit discard  
4. Legacy settings / storage paths → G5 matrix  

---

## Append log

### 2026-07-07 — KAIRO Ask persona for composer Ask mode

- `kairo_ask_prompt.py` supplies KAIRO voice/tone for Lane B Ask mode when `operator_persona_enabled` is on.
- Neutral Lane B copy remains when persona is disabled.

### 2026-07-07 — UX-IDE-2 interrupt panel + IDE layout polish

- `IdeInterruptPanel` surfaces approvals, signals, and degraded runtime in IDE interrupt tier.
- IDE uses the same topbar `KairoPresenceBar` as operator; interrupt stop routes to `stopIdeAgentRun` when the IDE agent stream is active (G3.4 parity).

### 2026-07-06 — Execution track opened + G3.8 started

- Published this track document.
- G3.8: `execution_access` API, approval gate wiring, Agent Dock Full Access toggle.

### 2026-07-06 — G3.8 Full Access agent slice landed

- Full Access consent replaces per-run approval; Cursor stream-json + transcript blocks.
- Successful IDE agent runs auto-complete; operator thread isolation fixed.
- KAIRO milestone narration + JARVIS voice script (browser TTS — cloud TTS deferred to Wave 3).
- **Resume here:** Wave 3 slice 9 — **UX-IDE-2** `IdeInterruptPanel`.

### 2026-07-06 — UX-IDE-1 quiet IDE presence profile

- `ide-presence-profile.ts` derives quiet/assist/interrupt tiers from run/signal/watch state.
- IDE mode uses `KairoChip` (not radar), collapses KAIRO sidebar to compact chip, and hides healthy watch + ops telemetry from status bar.

### 2026-07-06 — G3.6 + G3.7 orchestration gate closed

- G3.6: `tests/test_agent_orchestration_parity.py` maps IMPORT_MATRIX runtime rows to bounded owners and verifies IDE agent workflow receipts + run-state truth.
- G3.7: `npm run verify:agent-orchestration-parity` green; gate includes parity, MCP registry, lane B dispatch, and process-registry tests.
- Fixed vault integration test isolation when host Cursor CLI is OAuth-signed-in.

### 2026-07-06 — G3.4 + G3.5 landed in parallel

- G3.4: IDE Stop targets linked agent run, tears down stream, `stop_run` terminates `process_registry`.
- G3.5: MCP tools filtered by composer mode in dispatch metadata; Agent Dock Tools panel reads `/api/runtime/mcp-tools`.
