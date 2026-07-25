# Phase G5 — Capability Matrix (Axon-X vs Axon-Signal)

**Opened:** 2026-07-07  
**Branch:** `dev`  
**Primary operator URL:** http://127.0.0.1:4173  
**Fallback (explicit only):** http://127.0.0.1:7734  

## Purpose

Map every `docs/planning/IMPORT_MATRIX.md` row marked **`adopt`** or **`adapt`** to an Axon-X owner, verification gate, and current status. Cross-link `config/legacy-connector-inventory.json` and `config/parity-snapshot.json` blocker IDs.

**UI work is deferred** in this planning pass — matrix notes API/backend owners only; presentation slices live in `docs/planning/KAIRO_BRAIN_UI_ARCHITECTURE.md` deferral register.

## Status legend

| Status | Meaning |
|--------|---------|
| **done** | Gate green; operator can rely on Axon-X for this capability |
| **partial** | Backend or thin slice exists; known gap documented |
| **deferred** | Explicit operator-approved deferral (see G5.4) |
| **planned** | Owner named; gate not yet green |

## Product concepts

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| Operator control-plane thesis | adopt | control-plane | `services/control-plane/` | `verify:production-operator` | **done** | — |
| Multi-workspace oversight | adopt | control-plane + console-web | `workspace_catalog.py`, shell store | `verify:test0`, `verify:test1` | **done** | — |
| Attention / inbox concept | adapt | axon-watch + control-plane | `signals/`, `/api/inbox`, `/api/briefing` | `verify:parity-a4`, `verify:test5` | **done** | — |
| Workspace handoffs | adapt | control-plane | `handoff_store.py`, `/api/workspaces/{id}/handoffs` | `verify:test2` | **done** | — |
| Mission terminology | adapt | product docs | `docs/planning/PRODUCT.md`, mission control copy | doc review | **partial** | Wording drift vs axon-local; non-blocking |

## Frontend / UX patterns (backend + contracts only; UI deferred)

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| Operator vs IDE mode concept | adopt | console-web store + ADRs | `stores/shell.ts`, ADR-007/008 | `verify:test0`, ADR review | **done** | UI polish deferred (`UX-DEF-*`) |
| Agent dock behavior | adapt | console-web | `components/ide/AgentDock*` | `verify:agent-dock-parity` | **done** | `agent_dock_legacy_parity` — G4.5 closed |
| Workbench status hierarchy | adapt | console-web + control-plane | `runtime-strip.ts`, `/api/runtime/summary` | `verify:parity-b2`, `verify:parity-b3` | **done** | — |
| Workspace tab concept | adapt | console-web | `AgentDockWorkspaceMenu`, shell store | `verify:test0` | **done** | — |
| Signal/inbox surfaces | adapt | console-web + control-plane | inbox/briefing DTO consumers | `verify:parity-a4` | **done** | Richness gaps → DTO panels, not DB UI |

## Backend architecture

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| Proactive watcher concept | adapt | axon-watch | `services/axon-watch/app/signals/` | `verify:test4`, `verify:parity-d1` | **done** | — |
| Signal correlation | adapt | axon-watch | signal ranking + watch store | `verify:parity-a4` | **partial** | Full correlation graph deferred |
| Operator recommendations | adapt | control-plane | `operator_briefing.py`, `/api/briefing` | `verify:parity-c2`, `verify:test7` | **done** | — |
| Runtime truth discipline | adopt | control-plane | `run_store.py`, ADR-002 | `verify:phase-a`, `verify:agent-orchestration-parity` | **done** | — |

## Execution model

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| ReAct-style reasoning within a step | adapt | cli_runtime (bounded node) | `cli_runtime/cursor_agent.py` | `verify:agent-orchestration-parity` | **done** | Not system truth — ADR-004 |
| Exact approval boundaries | adopt | control-plane | `approval_gate.py`, run phases | `verify:parity-a2`, G3.3 tests | **done** | — |
| Plan mode concept | adapt | control-plane + lane B | composer modes, run phases | `verify:agent-orchestration-parity` | **done** | — |

## Runtime / AI orchestration

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| Cursor CLI agent loop | adapt | control-plane | `cli_runtime/cursor_agent.py` | `verify:cli-runtime`, `verify:agent-orchestration-parity` | **done** | `agent_orchestration` — replaced |
| Codex CLI agent loop | adapt | control-plane | `cli_runtime/codex_agent.py` | same | **done** | — |
| CLI binary catalog / resolve | adapt | control-plane | `cli_runtime/catalog.py` | `verify:cli-runtime` | **done** | — |
| Cursor → Codex reroute / recovery | adapt | control-plane | `cli_runtime/recovery.py` | `verify:cli-runtime` | **done** | — |
| Cursor cloud agents / automations | adapt | control-plane | `cli_runtime/cloud_cursor.py` | `verify:cli-runtime` | **partial** | Cloud path smoke only |
| Codex cloud tasks | adapt | control-plane | `cli_runtime/cloud_codex.py` | `verify:cli-runtime` | **partial** | — |
| Model Context Protocol (MCP) | adopt | control-plane | `/api/runtime/mcp-tools`, dispatch metadata | G3.5 tests in `verify:agent-orchestration-parity` | **done** | — |

## Delivery / notifications

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| Notification policy concept | adapt | axon-watch | delivery policy + receipts | `verify:test5`, `verify:parity-d2` | **done** | Native push/Slack install deferred |
| Push / desktop / webhook delivery | adapt | axon-watch | `delivery/adapters/` | `verify:parity-d2` | **partial** | File-based desktop ledger v1 |

## KAIRO / operator presence

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| JARVIS operator loop → KAIRO | adopt | product + services | `KAIRO_MODE.md`, briefing rhythm | `verify:parity-c2`, `verify:test6` | **done** | — |
| `watch_rule_for_item()` semantics | adapt | axon-watch | `signals/watch_rule.py` | `verify:test6` | **done** | — |
| `jarvis_personality.py` → persona | adapt | control-plane | `kairo_persona.py`, `kairo_ask_prompt.py` | `verify:parity-c1` | **done** | Full JARVIS identity options deferred |
| `toggleJarvisMode()` → presence settings | adapt | control-plane + console-web | `/api/operator-presence/settings` | `verify:test7`, `verify:parity-c1` | **done** | UI settings panel exists; galaxy deferred |
| VCD / voice deck orchestration | adapt | console-web | `features/voice-deck/` | `verify:voice-cockpit`, `verify:parity-d5` | **partial** | `voice_deck_mobile_cockpit` — foreground v1 |
| Voice attention polling → events | rewrite | console-web + SSE | `live-events-session.ts`, `live_events.py` | `verify:voice-cockpit` | **done** | Heartbeat SSE — see `OPERATOR_REFRESH_POLICY.md` |
| Executive operator workflow | adapt | control-plane | briefing `executive_rhythm` | `verify:parity-c2` | **done** | Template strings v1 |
| Mobile JARVIS controller | adapt | console-web | `viewport-compact.ts`, mobile shell class | `verify:parity-c3` | **done** | Native shell deferred |

## Data / persistence

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| SQLite local-first posture | adopt | both services | `run_store_sqlite.py`, `watch_store_sqlite.py` | `verify:parity-d1` | **done** | — |
| Split ownership by concern | adapt | persistence adapters | ADR-003 boundary | ADR review + store layout | **done** | No generic DB UI |
| Secure vault (full crypto) | adapt | axon-watch vault + CP routes | `services/axon-watch/app/vault/*` | `verify:vault-parity`, `verify:runtime-vault-integration` | **done** | `/vault` UI exists; UI polish deferred |
| DashPro external monitors | adapt | axon-watch monitors | `services/axon-watch/app/monitors/` | `verify:dashpro-monitors` | **partial** | `dashpro_external_monitors`; WhatsApp separate |

## Developer experience

| IMPORT_MATRIX capability | Disposition | Axon-X owner | Module / path | Gate | Status | Blocker / inventory |
|--------------------------|-------------|--------------|---------------|------|--------|---------------------|
| Guardrail mindset | adopt | repo scripts + docs | `scripts/guardrails/`, planning FITNESS | `verify:contracts` subset | **done** | axon-watch guardrails lighter than axon-local |
| Thin-slice delivery discipline | adopt | Phase G/F tracks | `PHASE_G_*`, verify scripts | slice gates | **done** | — |

## Legacy connector cross-map (inventory → Phase G)

| Inventory ID | Phase G slice | Matrix rows touched | Gate | Status |
|--------------|---------------|---------------------|------|--------|
| `agent_orchestration` | G3 | Runtime / execution rows | `verify:agent-orchestration-parity` | **done** |
| `cloudflare_tunnel` | G4.3 | Delivery + child integration | `verify:tunnel-remote-control` | **partial** |
| `voice_deck_mobile_cockpit` | G4.4 | KAIRO voice rows | `verify:voice-cockpit` | **partial** |
| `agent_dock_legacy_parity` | G4.5 | Agent dock row | `verify:agent-dock-parity` | **done** |
| `whatsapp_web_monitor` | G4.2 | DashPro monitors (related) | — | **deferred** |
| `legacy_settings_storage` | G5 | Dev experience + settings | G5.1 (this doc) | **planned** |
| `axon_local` | G6 | Fallback surface | operator sign-off | **planned** |

## G5 slice checklist

- [x] **G5.1** This capability matrix published
- [x] **G5.2** Extended production operator regression (`verify:signal-parity-matrix` — see `PHASE_G5_GATE_DESIGN.md`) — PASS verified 2026-07-07 (TEST-26 re-run on dev)
- [x] **G5.3** Refresh `config/parity-snapshot.json` assessment scope + blockers (2026-07-07); `full_axon_local_retirement` stays false until G6
- [ ] **G5.4** Operator acknowledgment of intentional discards (`PHASE_G5_INTENTIONAL_DISCARDS.md`) — doc published; ack boxes open

## References

- `docs/planning/IMPORT_MATRIX.md`
- `config/legacy-connector-inventory.json`
- `config/parity-snapshot.json`
- `docs/PHASE_G5_GATE_DESIGN.md`
- `docs/PHASE_G5_INTENTIONAL_DISCARDS.md`
