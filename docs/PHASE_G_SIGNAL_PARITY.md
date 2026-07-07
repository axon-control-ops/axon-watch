# Phase G — Full Signal Parity & Vault II

**Opened:** 2026-07-06  
**Precondition:** Phase F slices F0–F5 complete (`docs/PHASE_F_OPERATOR_FOUNDATION.md`)  
**Primary operator URL:** http://127.0.0.1:4173  
**Fallback URL:** http://127.0.0.1:7734 (explicit only until G6 sign-off)

## Purpose

Phase G is the locked follow-on after Phase F.

Axon-X must be able to do **everything Axon-Signal (`axon-local` :7734) can do today** — and do it **better and faster** — before full retirement is even considered.

Phase F proved the operator foundation (runtime fabric, thin `/vault`, `/data`, DashPro monitors, shell polish). Phase G closes the **capability gaps** that still force `:7734` fallback:

- full encrypted vault parity (Vault II)
- agent orchestration without the legacy ReAct monolith
- unmigrated connectors and operator surfaces
- retirement gates tied to evidence, not aspiration

## North star

| Axon-Signal today | Axon-X target |
|---|---|
| `brain.py` in-process ReAct loop | Control-plane run truth + Cursor/Codex runtime fabric |
| Transcript-inferred run state | SQLite persisted phases, receipts, approvals (`ADR-004`) |
| Alpine + giant JS modules | Vue console-web bounded features |
| Scheduler/polling monitors | Watch signal fabric + vault-fed probes |
| Plain `vault-import.json` stub (F2) | Full AES-256-GCM vault with session, 2FA, CRUD, export |
| Implicit LLM key resolution in `vault.py` | Explicit provider resolution feeding `cli_runtime` |

**Better:** explicit state, bounded modules, contract tests, operator-visible diagnostics.  
**Faster:** delegate heavy reasoning to Cursor/Codex CLIs (local + cloud) instead of a single Python ReAct loop; event-driven signals instead of scattered polling.

## Execution model — ReAct is not the backbone

This is already locked in planning. Phase G implements it end-to-end.

### Rejected as system truth

Pure prompt-driven ReAct as the primary execution source of truth — the classic `brain.py` loop on `:7734`.

Sources:

- `docs/planning/PRODUCT.md` — non-goal
- `docs/planning/ADR-004-execution-state-model.md` — accepted
- `docs/adr/ADR-002-control-plane-run-truth-and-briefing-seam.md`
- `docs/planning/IMPORT_MATRIX.md` — `ReAct-style reasoning within a step` = `adapt`, not adopt as backbone

### Approved stack (the better way)

```text
Operator intent
    → control-plane persisted run (phases, approvals, receipts)
    → runtime fabric routes work to:
         Cursor CLI  — primary live interactive runtime (Ask / Plan / Agent)
         Codex CLI   — primary scripted / batch / automation runtime
         MCP         — native tools contract
    → watch signals + KAIRO rhythm (notice → advise → approve → execute → verify)
    → verification receipts back into run store
```

ReAct-style step reasoning may still appear **inside** a bounded execution node (e.g. a Cursor agent turn), but:

- run phase, stop/resume, approval boundaries, and review-ready state come from **persisted run records**, not transcript parsing
- orchestration truth lives in `services/control-plane/`, not in prompt text
- legacy `brain.py` is a **donor**, not a port target

Phase G slice **G2** replaces the remaining `:7734` agent loop dependency with runtime-fabric-backed orchestration.

## Lock rule

1. Execute slices in the locked order below unless the operator reprioritizes explicitly.
2. One slice per pass; run the slice gate before starting the next.
3. `verify:vault-surface` (F2) ≠ vault parity. Do not conflate them.
4. Full axon-local retirement (G6) requires **all** G1–G5 gates green **and** operator sign-off.
5. New discoveries go into the append log; they do not silently reshuffle the order.

## Current state (2026-07-06)

| Area | Status |
|---|---|
| Phase F (F0–F5) | **Complete / gates green** |
| F6 retirement review | **Deferred to G6** |
| Vault II (full crypto) | **Complete** (`verify:vault-parity`) |
| Runtime-fed LLM provider keys | **Complete** (`verify:runtime-vault-integration`) |
| Agent loop parity (no `:7734` ReAct) | **In progress** (persisted runs + runtime stop wiring landing) |
| Legacy connectors (WhatsApp, tunnel, voice) | **Unmigrated** (`docs/LEGACY_CONNECTOR_INVENTORY.md`) |
| Full axon-local retirement | **Not approved** |

## Locked order

### G0 — Governance and parity baseline

- [ ] **G0.1** Publish this checklist (Phase G lock)
- [ ] **G0.2** Extend `docs/LEGACY_CONNECTOR_INVENTORY.md` with Vault II + orchestration rows
- [ ] **G0.3** Add Phase G track to `docs/planning/IMPLEMENTATION_ROADMAP.md`
- [ ] **G0.4** Refresh `config/parity-snapshot.json` assessment scope for post–Phase F state
- [ ] **G0.5** Sync planning mirror to axon-local `Plans/Axon-Watch/`

**Exit gate:** docs updated, mirror synced, parity baseline explicit.

---

### G1 — Vault II (full Signal vault parity)

Phase F F2 delivered import/status/consumer UX only (`vault-import.json`, 9-key allowlist, no secret values over API). Vault II ports the **behavior** of axon-local `vault.py` + `axon_api/routes/vault.py` + `ui/js/vault.js` into bounded Axon-X modules — not as a monolith copy.

#### Donor → bounded owner map

| Donor (axon-local) | Axon-X owner (target) |
|---|---|
| `vault.py` crypto (AES-256-GCM, KDF, TOTP) | `services/axon-watch/app/vault/crypto.py` |
| SQLite secret store + categories | `services/axon-watch/app/vault/store.py` |
| Session unlock/lock + auto-unlock keyfile | `services/axon-watch/app/vault/session.py` |
| Provider key resolution | `services/axon-watch/app/vault/provider_keys.py` |
| CSV / backup import-export | extend `services/axon-watch/app/vault/csv_import.py` + `backup.py` |
| HTTP routes | `services/control-plane/app/vault/routes.py` (expand) |
| Operator UI | `apps/console-web/src/components/vault/*` (full deck) |

#### G1 checklist

- [x] **G1.1** Extract crypto primitives (derive, encrypt/decrypt, TOTP, QR) with unit tests; wire-compatible with existing Signal vault backups where feasible
- [x] **G1.2** SQLite vault store (categories, metadata, encrypted payloads); explicit schema migration from F2 `vault-import.json` path
- [x] **G1.3** Session APIs: setup, unlock, lock, status; master password + TOTP 2FA parity
- [x] **G1.4** Auto-unlock keyfile (optional operator path) with same security posture as donor
- [x] **G1.5** Secret CRUD APIs: list, get (decrypted in-session only), create, update, delete
- [x] **G1.6** Import/export parity: backup JSON, CSV (axon format), merge vs replace semantics
- [x] **G1.7** Provider key resolution API for LLM runtimes (feeds G2); never log secret values
- [x] **G1.8** Full `/vault` UI: unlock deck, secret table, category filters, import/export flows, consumer readiness rail (extend F2)
- [x] **G1.9** Expand consumer map beyond DashPro monitors (document each required key per integration)
- [x] **G1.10** Migration script: Signal vault → Axon-X vault (operator-run, verified receipt)
- [x] **G1.11** Gate script + focused tests

**Exit gate:** `npm run verify:vault-parity`

**Explicit non-goals for G1:** cloud sync, multi-operator concurrent vault editing, HSM — defer unless reprioritized.

---

### G2 — Runtime secrets and orchestration wiring

Vault II secrets must actually drive the runtime fabric (Phase F F1), not sit in a UI silo.

- [x] **G2.1** `cli_runtime` catalog resolves LLM/auth keys from unlocked vault session (not env stubs)
- [x] **G2.2** Runtime health reflects vault-unlocked vs locked vs missing-key states
- [x] **G2.3** IDE composer + Agent Dock show actionable vault-unlock prompts when keys missing
- [x] **G2.4** Codex/Cursor cloud paths use same provider resolution contract
- [x] **G2.5** Gate script + focused tests

**Exit gate:** `npm run verify:runtime-vault-integration`

---

### G3 — Agent orchestration parity (replace `:7734` ReAct loop)

Close the largest functional gap in `docs/LEGACY_CONNECTOR_INVENTORY.md` item 1.

- [x] **G3.1** Define orchestration contract: operator command → run record → runtime fabric dispatch → normalized events → receipts
- [x] **G3.2** Wire Mission Control / Agent Dock chat to runtime fabric sessions (Cursor primary, Codex fallback per `cli_runtime/recovery.py`)
- [x] **G3.3** Preserve approval boundaries: no silent tool execution outside `executing` phase
- [x] **G3.4** Stop/resume/cancel maps to runtime process control, not prompt cancellation alone
- [x] **G3.5** MCP tool surface registered in control-plane; no ad hoc tool strings in shell
- [x] **G3.6** Parity tests against donor workflows (bounded set from `IMPORT_MATRIX` runtime section)
- [x] **G3.7** Gate script + focused tests
- [x] **G3.8** Full Access composer toggle + `execution_access` API (Codex/Cursor executing tier after approve)

**Exit gate:** `npm run verify:agent-orchestration-parity`

**Note:** This slice **does not** reintroduce `brain.py`. It completes the architecture Phase F started.

---

### G4 — Legacy connector migration

Per `config/parity-snapshot.json` → `blockers_for_full_retirement` and `docs/LEGACY_CONNECTOR_INVENTORY.md`.

- [x] **G4.1** Inventory each unmigrated connector with owner, probe, and fallback removal criteria
- [ ] **G4.2** WhatsApp / external messaging — bounded watch integration or explicit discard with operator approval
- [x] **G4.3** Tunnel / remote control — auth + binary + live status in connectors rail (operator foundation rule)
- [x] **G4.4** Voice deck / mobile cockpit — event-driven presence (`IMPORT_MATRIX` KAIRO section)
- [x] **G4.5** Remaining Agent Dock parity items from `parity-snapshot.json`
- [ ] **G4.6** Gate script per connector or bundled `verify:connector-parity`

**Exit gate:** `npm run verify:connector-parity` (or per-connector gates documented in G4.1)

---

### G5 — Full capability matrix gate

Prove Axon-X ≥ Signal for operator daily work, not just thin-slice behaviors.

- [ ] **G5.1** Generate capability matrix: every `IMPORT_MATRIX` row marked `adapt`/`adopt` has Axon-X owner + gate
- [ ] **G5.2** Run extended production operator regression (F5 gate + G1–G4 gates)
- [ ] **G5.3** Update `config/parity-snapshot.json`: `full_axon_local_retirement` candidate flag only if all gates green
- [ ] **G5.4** Document known intentional discards (`IMPORT_MATRIX` `discard` rows) with operator acknowledgment

**Exit gate:** `npm run verify:signal-parity-matrix`

---

### G6 — Retirement readiness (was F6)

- [ ] **G6.1** Reassess `blockers_for_full_retirement` with G1–G5 evidence
- [ ] **G6.2** Operator dry-run: one full week on `:4173` only for DashPro + Axon workspaces
- [ ] **G6.3** Decide whether axon-local process can move to archive / explicit fallback-off mode
- [ ] **G6.4** Add `test17-full-retirement-readiness.sh` only if G1–G5 gates are green

**Exit gate:** explicit operator sign-off only — no automated gate substitutes for this slice.

## Per-slice workflow

Same as Phase F:

1. Bounded module first; no monolith growth
2. Add or amend a doc/spec when behavior is non-trivial
3. Add the cheapest reliable verification in the same slice
4. Keep runtime policy explicit and observable
5. Append log entry; do not rewrite history

## Relationship to Phase F gates

| Phase F gate | What it proved | What Phase G adds |
|---|---|---|
| `verify:vault-surface` | Route, import UX, consumer map | Full crypto vault (G1) |
| `verify:cli-runtime` | Runtime fabric exists | Vault-fed keys + orchestration (G2, G3) |
| `verify:production-operator` | Shell polish | Full parity regression (G5) |
| F6 retirement | Deferred | G6 with evidence |

## Append log

### 2026-07-07 — G4.4 + G4.5 voice cockpit and Agent Dock parity

- G4.4: `presence_refresh` live events, reactive voice-cockpit spoken-alert delivery, mobile compact strip (foreground-only).
- G4.5: dock hero mode persistence, operator thread seam collapse, IDE agent transcript summary header.
- Gates: `verify:voice-cockpit`, `verify:agent-dock-parity`.

### 2026-07-07 — G4.3 tunnel remote control slice

- Watch tunnel probe reports binary, auth source, process state, and public health in connectors rail.
- Control-plane `/api/tunnel/status|start|stop` proxies watch; console Connectors rail exposes tunnel actions.
- Gate: `npm run verify:tunnel-remote-control`.

### 2026-07-07 — G4.1 legacy connector inventory

- Published `config/legacy-connector-inventory.json` with owner, probe, Phase G slice, and removal criteria per connector.
- Gate: `npm run verify:connector-inventory` (`test21-connector-inventory.sh`).
- Retirement blocker map ties `parity-snapshot.json` blockers to inventory IDs.

### 2026-07-06 — G2 runtime vault integration implemented

- `cli_runtime` catalog consumes watch vault runtime posture + internal runtime-env keys.
- `/api/runtime/status` now includes `vault_runtime` posture and per-target `auth.vault_posture`.
- IDE Agent Dock shows vault-locked chip + **Open Vault** CTA in composer runtime menu.
- Cursor/Codex subprocesses receive vault-fed `CURSOR_API_KEY` / `CODEX_API_KEY` / `OPENAI_API_KEY`.
- Gate: `npm run verify:runtime-vault-integration` (`test19-runtime-vault-integration.sh`).

### 2026-07-06 — G3.8 Full Access UI + execution track

- Published `docs/PHASE_G_EXECUTION_TRACK.md` and `docs/planning/agent-orchestration-contract.md`.
- Composer **Full Access** toggle (`execution_access: full`) in Agent Dock; approval banner with Approve/Reject.
- Backend: `lane_b_run_dispatch.py`, API field on `POST /api/chat/messages`, approval gate uses access tier.
- Tests: `tests/test_lane_b_run_dispatch.py`, updated approval gate + chat integration tests.

### 2026-07-06 — G3.3 approval boundaries for runtime fabric

- Added `cli_runtime/approval_gate.py`: consultative tier by default; tool execution only when `AXON_WATCH_AGENT_TOOL_EXECUTION=1` and run phase is `executing`.
- Lane B Agent runs enter `awaiting_approval` when tool execution is enabled; Cursor uses `--mode plan` until approved, then `--mode agent`.
- Codex switches from read-only sandbox to workspace-write only in executing tier.
- Tests: `tests/test_cli_runtime_approval_gate.py`, chat integration for approval-boundary agent runs.

### 2026-07-06 — G3 runtime process stop + agent run surfacing

- CLI runtime subprocesses register against persisted `run_id` during agent dispatch.
- `stop_run` now terminates in-flight Cursor/Codex CLI processes via `process_registry`.
- Agent-mode lane B creates the run **before** runtime dispatch so stop can cancel execution.
- Agent Dock refreshes run surfaces after composer submit and expands the run seam when a run is linked.
- Thread messages show linked `run_id` chips for traceability.

### 2026-07-06 — G1/G2 upgrade pass and G3 bootstrap

- Bootstrap now installs Python deps into repo `.venv` via `requirements.txt` and `scripts/dev/ensure-python-deps.sh`.
- Vault consumer readiness now includes Cursor/Codex/OpenAI runtime surfaces in addition to DashPro monitor keys.
- `scripts/ops/import-vault-from-signal.py` can now target the encrypted vault path directly with `--encrypted-vault`.
- Control-plane runtime surfaces now expose an explicit MCP registry (`/api/runtime/mcp-tools`).
- Lane B `agent` mode now records a persisted run, runtime-dispatch receipt, and review-ready transition instead of remaining thread-only.
- Gate scaffold: `npm run verify:agent-orchestration-parity` (`test20-agent-orchestration-parity.sh`).

### 2026-07-06 — G1 Vault II implemented

- Full AES-256-GCM vault with SQLite store, TOTP 2FA, session unlock/lock, auto-unlock keyfile.
- All 15 Signal-compatible vault API routes on control-plane (`/api/vault/*`).
- `/vault` UI: setup, unlock, secrets CRUD, backup/CSV export, monitor-key import.
- Gate: `npm run verify:vault-parity` (`test18-vault-parity.sh`).
- Migration helper: `scripts/ops/migrate-signal-vault-to-axon-x.py`.
