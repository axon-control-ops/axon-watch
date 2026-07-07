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
| 11 | **UX-IDE-3** | Research cards in agent transcript | JARVIS video | **Done** |
| 12 | **UX-IDE-4** | `@selection`, `@terminal` context tokens | JARVIS “pull up notes” | **Done** |
| 13 | **UX-IDE-5** | Opt-in IDE voice strip | JARVIS hands-free (later) | **Done** |

---

## Wave 4 — Retirement path (G4 → G6)

| # | Slice | Deliverable | Gate | Status |
|---|---|---|---|---|
| 14 | **G4.1** | Connector inventory with probe + removal criteria | `verify:connector-inventory` | **Done** |
| 15 | **G4.3** | Tunnel / remote control — binary + auth + live status in connectors rail | `verify:tunnel-remote-control` | **Done** |
| 16 | **G4.4** | Voice deck / mobile cockpit — event-driven presence | `verify:voice-cockpit` | **Done** |
| 17 | **G4.5** | Agent Dock parity gaps (hero persist, thread meta, collapsible seam) | `verify:agent-dock-parity` | **Done** |
| 18 | **G4.2** | WhatsApp — bounded watch integration or explicit discard | DashPro `:7734` fallback | **Deferred** |
| 19 | **G4.6** | `verify:connector-parity` bundled gate | `test25-connector-parity-bundle.sh` | **Done** |
| 20 | **G5** | Capability matrix + gate design + discards docs | `verify:signal-parity-matrix` (TEST-26) | **Done** |
| 21 | **G6** | One week `:4173` only + operator sign-off | **Retirement** | — |

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

**Wave 4 exit:** G4.1–G4.6 gates green (G4.2 WhatsApp deferred with operator approval). **Wave 5 exit:** TEST-26 (`verify:signal-parity-matrix`) green on `dev`. **Next:** **G6** one-week `:4173`-only dry-run + operator sign-off.

**UI deferred (planning handoff):** No new `apps/console-web/**` — see `docs/planning/KAIRO_BRAIN_UI_ARCHITECTURE.md` (`UX-DEF-*`). Backend/gates/orchestration only.

**Next up:** **G6.2** one-week `:4173`-only dry-run + sign-off. **G4.2 WhatsApp deferred.** **G5.3** retirement flag stays false until G6.

---

## What still forces `:7734`

1. Agent loop with file edits → Wave 1–2 (**done** on axon-watch)  
2. Child-project connectors (WhatsApp deferred, tunnel partial on Axon-X) → G4  
3. Voice / mobile cockpit → G4.4 (**done** on Axon-X; foreground-only v1)  
4. Legacy settings / storage paths → G5 matrix  

---

## Append log

### 2026-07-07 — Phase 4/5 closure + resume bugfixes

- Fixed IDE Resume: composer shows Resume over Stop when run is paused; consultative + full-access re-dispatch resumes `paused`/`review_ready` runs (no duplicate runs).
- Fixed `IdeInterruptPanel` Resume to target IDE agent run (parity with Stop).
- Fixed stream errors surfacing in composer; agent stream exceptions park runs at `review_ready`.
- Aligned `legacy-connector-inventory.json` retirement_blocker_map with refreshed parity snapshot.
- Gates green: `verify:connector-parity` (TEST-25), `verify:signal-parity-matrix` (TEST-26), `verify:headed-browser-smoke`.
- **G5.4 operator acks still open** — human sign-off before Phase 6/7.

### 2026-07-07 — G5.0-triage + G5.3 snapshot + headed browser smoke + TEST-17

- Regenerated `docs/planning/MANIFEST.json`; TEST-3/9 decoupled from full `npm run verify`.
- Refreshed `config/parity-snapshot.json` assessment scope + granular retirement blockers (G5.3).
- Added `npm run verify:headed-browser-smoke` (Playwright shell/operator/IDE + screenshots).
- Added `npm run verify:retirement-readiness` (TEST-17 spec; requires G6.2 + discard acks).
- Reconciled stale docs: `PHASE_G_SIGNAL_PARITY.md`, `PHASE_G5_CAPABILITY_MATRIX.md`, `IMPLEMENTATION_ROADMAP.md`, `FINAL_PARITY_VERIFICATION.md`.
- **Next:** G6.2 one-week `:4173`-only dry-run + operator discard acks.

### 2026-07-07 — G5 gate green (TEST-26)

- `npm run verify:signal-parity-matrix` PASS (12/12) — contracts, console-web, G1–G4 bundles, phase A/B/D, production-operator, planning manifest, G5.1 doc.
- Phase A/B/D scripts decoupled from `npm run verify` monolith; Phase B snapshot counts now computed from `parity-snapshot.json` behaviors (verified_v1=19, partially_verified=0).
- **G5.3 deferred:** `full_axon_local_retirement` stays `false` until G6 operator sign-off.
- **Next:** G6.2 one-week `:4173`-only dry-run (human gate).

### 2026-07-07 — G5/G6 planning handoff (UI deferred)

- Published: `PHASE_G5_CAPABILITY_MATRIX.md`, `PHASE_G5_INTENTIONAL_DISCARDS.md`, `PHASE_G5_GATE_DESIGN.md`, `PHASE_G6_RETIREMENT_READINESS.md`.
- Published: `docs/planning/KAIRO_BRAIN_UI_ARCHITECTURE.md`, `docs/planning/OPERATOR_REFRESH_POLICY.md`.
- Wave 4 closed on `dev`; `verify:connector-parity` = TEST-25 (not full `npm run verify`).
- JARVIS pack: adopt loop/personality/prove-source/server brain; reject galaxy + keyword RAG.
- Blockers: planning MANIFEST drift; TEST-3/9 full verify hooks — see G5 gate design.
- Dirty files off limits: `lane_b_git_dispatch.py`, `workspace_git.py`, `kairo_voice.py`, related tests.

### 2026-07-07 — G4.6 connector parity bundle (Wave 4 exit)

- Added `scripts/verify/test25-connector-parity-bundle.sh` — scoped bundle for G4.1 inventory + TEST-3 connector slices + G4.3–G4.5 gates (no full-repo `npm run verify`).
- `npm run verify:connector-parity` now runs TEST-25.
- Runtime proof: Playwright visual smoke at `.local/verify/g4-visual-proof/` (IDE thread meta, operator thread collapse, mobile strip stability).
- Fixed operator thread seam collapse (`dock-seam-layout` + default `expandedDockSeams` includes `thread`).
- Briefing fetch coalescing removes duplicate `/api/briefing` at the 10s presence/runtime overlap.

### 2026-07-07 — G4.4 + G4.5 voice cockpit and Agent Dock parity

- G4.4: event-driven voice cockpit via `presence_refresh` SSE, reactive briefing spoken-alert delivery, and mobile compact strip.
- G4.5: persisted dock hero mode, collapsible operator thread seam, and IDE agent transcript summary meta.
- Gates: `verify:voice-cockpit`, `verify:agent-dock-parity`.

### 2026-07-07 — G4.3 tunnel remote control on Axon-X

- `services/axon-watch/app/tunnel/*` probes cloudflared binary, auth sources (env/vault/legacy), process state, and public health.
- Connectors rail shows `cloudflare_tunnel` with Start/Stop (via axon-local `tunnel.sh`) and Open tunnel URL.
- Gate: `npm run verify:tunnel-remote-control` (`test22-tunnel-remote-control.sh`).

### 2026-07-07 — G4.1 legacy connector inventory

- `config/legacy-connector-inventory.json` lists owner, probe, Phase G slice, and fallback removal criteria per connector.
- `verify:connector-inventory` (`test21-connector-inventory.sh`) validates contract + parity-snapshot blocker map.
- `docs/LEGACY_CONNECTOR_INVENTORY.md` updated with G4.1 table.

### 2026-07-07 — UX-IDE-5 opt-in IDE voice strip

- `ide_voice_strip_enabled` setting (default off) gates IDE speech delivery and shows a bottom voice strip when enabled.
- Operator mode speech unchanged; IDE narration, spoken alerts, and boot greeting require opt-in.
- Settings toggle in Operator Presence panel; strip exposes live status and one-click hide.

### 2026-07-07 — UX-IDE-4 composer `@selection` and `@terminal` context tokens

- IDE composer Context menu adds `@selection` (Monaco highlight) and `@terminal` (recent scrollback).
- Lane B dispatch receives `editor_selection` and `terminal_snippet` and injects them into workspace context.

### 2026-07-07 — UX-IDE-3 research cards in agent transcript

- Web-search tool calls emit `:::research` blocks from Cursor stream-json assembly.
- Agent transcript renders JARVIS-style source cards with title, URL, and snippet.

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
