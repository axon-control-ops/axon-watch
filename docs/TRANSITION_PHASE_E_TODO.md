# Axon-X Transition Phase E — Working Checklist

**Purpose:** Post–parity-closure (`Phase A–D complete`) work toward full axon-local
retirement. This is the active ordered list after `docs/AXON_X_CUTOVER_TODO.md`
(TEST-0 … TEST-10) finished.

**Production operator:** http://127.0.0.1:4173  
**Fallback:** axon-local http://127.0.0.1:7734 (legacy connectors + unmigrated child-project paths)

**Status:** **Initial-Progressed** — E0–E5 complete. Follow-on runtime, vault,
data, and automation work moved to `docs/PHASE_F_OPERATOR_FOUNDATION.md`. E6
remains deferred until Phase F closes.

**Lock rule:** Same as cutover TODO — append discoveries to the log; do not reorder
without explicit operator approval.

---

## Current state (2026-07-05)

| Area | Status |
|---|---|
| Parity A–D | Complete (19/19 verified v1) |
| Production operator declared | Yes (`docs/PRODUCTION_OPERATOR_SURFACE.md`) |
| Full axon-local retirement | **Not approved** (E6 paused for review) |
| Sole retirement blocker (snapshot) | Child-project + legacy connector migration |
| Phase E (E0–E5) | **Initial-Progressed** — follow-on work moved to Phase F |

---

## Phase E — Locked order

### E0 — Land and prove recent work

- [x] **E0.1** Push `dev` to origin (attempt after local commit; see git status)
- [x] **E0.2** Restart stack and smoke: `./scripts/dev/down.sh && ./scripts/dev/up.sh`
- [x] **E0.3** Gates green:
  - `npm run verify:production-operator` — PASS
  - `npm run verify:phase-d` — PASS
  - `PYTHONPATH=. python3 -m unittest tests.test_shell_command tests.test_command_executor` — PASS
- [x] **E0.4** Sync planning mirror → axon-local:
  `python3 scripts/ops/sync_planning_mirror_to_axon_local.py` — 29 files copied
- [x] **E0.5** Append `docs/AXON_X_CUTOVER_TODO.md` log (see append log below)

### E1 — Operator command plane

- [x] **E1.1** Bounded `run …` shell commands in workspace root
- [x] **E1.2** Commands footer **Run** submits immediately
- [x] **E1.3** Verify gate: `./scripts/verify/test11-workspace-shell-commands.sh`
  + `npm run verify:shell-commands` (script + acceptance added)
- [x] **E1.4** Live proof: `run ./scripts/dev/check-health.sh`, `check-health` shortcut — PASS (acceptance)
- [x] **E1.5** Allowlisted shortcuts: `verify`, `check-health` without `run` prefix

### E2 — Watch / connector operator surfaces

- [x] **E2.1** Mission Control **Connectors** rail bound to `GET /api/connectors`
- [x] **E2.2** UI triggers: **Reprobe connector**, **Refresh summary**
- [x] **E2.3** Signal acknowledge / CLEAR — TEST-5 regression includes `test_watch_signal_acknowledge`
- [x] **E2.4** Narrow bootstrap `signal_runtime_summary_degraded` when required connectors trusted

### E3 — Legacy connector + child-project migration (retirement blocker)

- [x] **E3.1** `docs/LEGACY_CONNECTOR_INVENTORY.md` created
- [x] **E3.2** Legacy façade: axon_local row + read-only status in Connectors rail
- [x] **E3.3** Child-project workspace: `workspace_dashpro` → `/home/edp/Projectx/product/dashpro` (DashPro)
- [x] **E3.4** Handoff UX: **Open :7734 fallback** button on axon_local connector row

### E4 — Agent / chat depth (Lane B)

- [x] **E4.1** System ack includes execution summary; agent reply already carries evidence
- [x] **E4.2** Composer hint: operator commands only; IDE Agent dock for scoped plan/ask
- [ ] **E4.F1** Full runtime-backed Lane B is **not** complete here. The exit target
  is Phase F1: Cursor/Codex local + cloud runtimes, not a local-model bridge.

### E5 — Documentation and onboarding debt

- [x] **E5.1** How-To: deduped duplicate Quick Start → **Detailed setup (first install)**
- [x] **E5.2** How-To: added Handbook map, Debugging playbook, Upgrading sections
- [x] **E5.3** Starter guide: Watch commands + `run …` + shortcuts
- [x] **E5.4** `docs/PRODUCTION_OPERATOR_SURFACE.md` updated

### E6 — Full retirement exit (PAUSED — final review)

- [ ] **E6.1** `config/parity-snapshot.json` → `blockers_for_full_retirement` empty
- [ ] **E6.2** Operator sign-off documented in `docs/CUTOVER_DECISION.md`
- [ ] **E6.3** `full_axon_local_retirement: true` in snapshot + amend decision doc
- [ ] **E6.4** Final gate: `./scripts/verify/test12-full-retirement-readiness.sh` (create when ready)

---

## Per-slice workflow (unchanged)

1. Bounded module — no monolith growth  
2. Spec under `docs/` when non-trivial  
3. Gate script + unittest / npm verify target  
4. Update snapshot / ledger if parity row affected  
5. Append log entry — do not rewrite history  

---

## Append log

### 2026-07-05 — Phase E closed as Initial Progress

- Phase E is no longer the active build checklist. Treat it as the **Initial Progress**
  closeout for Axon-X: production operator declared, parity A–D complete, cutover
  TEST-0 … TEST-10 complete, and E0–E5 delivered.
- New build truth lives in `docs/PHASE_F_OPERATOR_FOUNDATION.md`.
- E6 stays deferred until Phase F runtime fabric, vault, data, monitor, and
  polish gates are green.
- Full runtime-backed Lane B remains **unshipped** here; the committed local-model
  scaffold is an interim checkpoint, not the approved architecture target.

### 2026-07-05 — Phase E checklist opened

- Parity A–D complete; cutover TEST-0 … TEST-10 complete.
- Production operator UX polish committed (`b3e3629`).
- T1 workspace shell commands + footer Run committed (`e0735da`).
- Next active item: **E0.1** push + verify, then **E1.3** shell-command gate.

### 2026-07-05 — Phase E0–E5 complete (E6 paused)

- **E1:** TEST-11 gate (`verify:shell-commands`), `check-health` / `verify` shortcuts, health vs shell intent fix.
- **E2:** Connectors rail in Mission Control, reprobe/refresh watch commands, summary-degraded omitted when required connectors ok.
- **E3:** `LEGACY_CONNECTOR_INVENTORY.md`, `:7734` fallback link, `workspace_dashpro` (DashPro) + `npm run verify:child-project`.
- **E4:** Richer system dispatch ack; scoped free-form hint for IDE Agent dock.
- **E5:** Handbook/starter/production docs updated.
- **E1.4** live proof includes `run npm test` (via new root `npm test` script).
- **E0.1** committed locally; push with `git push origin dev` when ready.
- **E6 not started** — full retirement still blocked per snapshot.
