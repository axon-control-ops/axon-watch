# Axon-X Locked Execution Plan

**Effective:** 2026-07-09  
**Operator URL:** http://127.0.0.1:4173  
**Fallback (emergency only):** http://127.0.0.1:7734  

This is the **single follow-to-the-letter checklist** for Axon-X work from today
through retirement sign-off. It consolidates Phase G6 dry-run, operator hygiene,
KAIRO conversation, and brain-galaxy polish into one locked order.

**Parent context (do not duplicate):**

- `docs/PHASE_G_EXECUTION_TRACK.md` — Phase G waves 1–5 history
- `docs/planning/OPERATOR_BRAIN_PIVOT.md` — operator second-brain direction
- `docs/planning/KAIRO_CONVERSATION_PLAN.md` — OP-C slice detail
- `docs/planning/KAIRO_VOICE_IMPROVEMENT_PLAN.md` — voice narration + context/memory slices
- `docs/PHASE_G6_RETIREMENT_READINESS.md` — G6 blocker table + rollback

---

## Lock rules

1. **One slice per pass.** Finish the current slice gate before starting the next.
2. **Debt gate.** If `review_ready` > 5 or zombie `executing` > 0, only hygiene
   and cleanup slices run until the debt gate clears.
3. **Append-only logs.** Discoveries go to slice append logs; do not reorder this
   plan without explicit operator approval.
4. **Primary surface.** Use `:4173` for daily work. Open `:7734` only for
   documented rollback (see Phase F rollback table).
5. **Agent boundaries.** Operator mode = commands, fleet, KAIRO, signals. IDE mode
   = file edits, terminal, Agent dock (Cursor CLI). Do not mix lanes in one turn.
6. **Bounded modules.** New UI in `apps/console-web/src/features/*`; new server
   logic in bounded packages under `services/*/app/` — no shell monolith growth.
7. **Truth from DTOs.** KAIRO answers and briefing copy come from persisted
   APIs, never from prompt invention.

---

## Current snapshot (2026-07-09)

| Area | Status |
|------|--------|
| Phase G waves 1–5 (orchestration, connectors, parity matrix) | **Done** |
| Phase F (runtime fabric, vault, data, monitors, polish) | **Done** |
| Operator brain pivot (fleet grid, galaxy, voice deck) | **Landed; polish ongoing** |
| OP-C1/C2/C3 conversation loop | **Landed; gates + hardening pending** |
| Hygiene O1–O3 (auto-complete, resume guard, quick guide) | **Landed in code** |
| Verification debt (35+ `review_ready`, 9 zombie `executing`) | **Cleared** (B1 dry-run: 0 stale runs) |
| G5.4 intentional discards operator ack | **Open — human sign-off** |
| G6.2 one-week `:4173`-only dry-run | **In progress** |
| Full axon-local retirement (E6) | **Deferred until this plan Phase F** |

**Branch:** `dev` (ahead of origin — push when operator approves).

---

## Phase A — Baseline (Day 0, ~30 min)

Run once before any build slice, and again each morning during the dry-run.

| Step | Action | Pass when |
|------|--------|-----------|
| A1 | `cd` repo root; `npm install` if deps changed | No install errors |
| A2 | `./scripts/dev/up.sh --no-open` | Stack starts |
| A3 | `./scripts/dev/check-health.sh` | All endpoints green |
| A4 | Open http://127.0.0.1:4173 — hard refresh (Ctrl+Shift+R) | Shell loads |
| A5 | `npm run verify:production-operator` | PASS |
| A6 | `npm run verify:headed-browser-smoke` | PASS |
| A7 | Record run-store snapshot in `docs/PHASE_G6_DRY_RUN_AUDIT_LOG.md` | Tick appended |

**Do not proceed to Phase B if A3 or A5 fails.**

---

## Phase B — Hygiene closeout (O1–O5)

**Goal:** Operator opens Axon and sees fleet insight, not a wall of Git status runs.

| ID | Slice | Work | Gate |
|----|-------|------|------|
| B1 | **O4 cleanup** | `./scripts/ops/operator-run-cleanup.sh` — clear verification debt | `review_ready` ≤ 5; zombie `executing` = 0 |
| B2 | **O1 proof** | Run `git status` + `check-health` in operator mode; confirm auto-complete | New one-shots land in `completed`, not parked |
| B3 | **O2 proof** | Attempt `resume from review` on a one-shot run | Run completes instead of re-entering `executing` |
| B4 | **O3 proof** | Open Attention quick guide for read-only command | Copy says COMPLETE, not RESUME |
| B5 | **O5 proof** | Switch workspaces; confirm briefing NOTICE matches active workspace scope | No global "36 runs" vs workspace "17" mismatch |
| B6 | **Acceptance hygiene** | After verify scripts, re-run B1 if debt reappears | Debt gate stays clear 24h |

**Phase B exit gate:** debt gate clear + `npm run verify:production-operator` PASS.

**If B1 cannot clear debt:** fix acceptance tests to complete/cancel runs they
create before claiming any later phase done.

---

## Phase C — KAIRO conversation loop (OP-C)

**Goal:** Operator can ask KAIRO "what needs attention?" and get a grounded answer
in under one second; typed and push-to-talk both work; actions require confirmation.

Detail: `docs/planning/KAIRO_CONVERSATION_PLAN.md`

| ID | Slice | Work | Gate |
|----|-------|------|------|
| C1 | **OP-C1 gate** | Harden `/api/kairo/converse` fast path (status questions, no CLI) | `python3 -m unittest tests.test_kairo_conversation -v` PASS; curl status Q < 1s |
| C2 | **OP-C2 gate** | Galaxy conversation bar: typed Q + command dispatch + spoken reply | Manual: "any approvals?" → spoken + written answer; "git status" → run dispatched |
| C3 | **OP-C3 gate** | Push-to-talk (hold orb / Space); privacy mode blocks mic | Manual: hold → speak → release → answer; privacy ON hides mic |
| C4 | **OP-C4** | Navigation intents ("show DashPro", "open attention"); execute-tier confirm flow | vitest `conversation-intents.test.ts` PASS; manual nav + confirm dispatch | **Done** |
| C5 | **OP-C5** | Session turn memory for follow-ups ("hand it off" after prior entity) | Contract tests for memory cap; manual follow-up without re-stating workspace | **Done** |
| C6 | **V5+V9** | Narration plumbing cleanup + honest settings copy | vitest narration tests PASS; no speak API calls for filtered milestones | **Done** |
| C7 | **V1+V4+V6** | Honest mode labels, persona parity for thinking, error/fallback narration | Manual: minimal thinking uses Vaxon tone; agent error spoken |
| C8 | **M1+M2** | Unified session id + SQLite-backed turn/entity memory | pytest: follow-up survives CP restart |
| C9 | **M3+M5+M6** | Chat tail in context pack, 10 s DTO refresh, unified voice-log dedup | pytest context pack + TTL; manual: no repeated phrasing across channels |
| C10 | **M4** | Agent continuation — inject KAIRO memory into Lane B dispatch | Manual: IDE agent continues KAIRO topic after handoff |
| C11 | **V2+V3+V7+V8** | Throttled thinking, optional tool narration, stale-speak cancel, IDE voice hint | Optional depth — does not block Phase D |
| C12 | **V11** | Cloud TTS | **Deferred** until Phase F exit |

Detail: `docs/planning/KAIRO_VOICE_IMPROVEMENT_PLAN.md`

**Phase C exit gate:** C1–C10 gates green + `npm run verify:headed-browser-smoke` PASS.
(C11 optional; C12 deferred.)

**Deferred until Phase C exit:** OP-C6 wake word, OP-V1g mobile shell.

---

## Phase D — Brain polish + handoff (OP-B6e, OP-V1f)

**Goal:** Galaxy node click opens prove-source; signal/monitor → Continue in IDE works end-to-end.

| ID | Slice | Work | Gate |
|----|-------|------|------|
| D1 | **OP-B6e** | Node click → prove-source panel (workspace, signal, monitor nodes) | Manual: click Sentry node → evidence panel; click workspace → focus |
| D2 | **OP-V1f / OP-B5** | Handoff card from incident feed + conversation artifact → IDE agent run | `npm run verify:test2` + manual handoff on DashPro signal |
| D3 | **OP-B4 close** | Live Sentry/PostHog in inbox; bootstrap suppressed when monitors fire | `npm run verify:dashpro-monitors` PASS |
| D4 | **OP-B3** | Run queue demoted to collapsible bottom strip (not hero) | Visual: fleet/brain is hero; run strip collapsed by default when idle |

**Phase D exit gate:** D1–D4 manual smoke + `npm run verify:connector-parity` PASS.

---

## Phase E — G6 dry-run week (`:4173` only)

**Goal:** Prove daily operator work without `:7734` except logged emergencies.

Detail: `docs/PHASE_G6_RETIREMENT_READINESS.md` § G6.2

### Daily ritual (~15–20 min)

| Step | Action |
|------|--------|
| E-daily-1 | Phase A baseline (A2–A7) |
| E-daily-2 | `./scripts/ops/g6-dry-run-monitor.sh` — append tick to audit log |
| E-daily-3 | `npm run verify:connector-parity` |
| E-daily-4 | Manual smoke for **today's workspace focus** (rotate Mon–Fri table below) |
| E-daily-5 | Log any forced `:7734` fallback with blocker ID + reason |

### Workspace rotation (one focus per weekday)

| Day | Workspace | Smoke tasks |
|-----|-----------|-------------|
| Mon | `workspace_smoke` | Operator command, run stop, Attention inbox |
| Tue | `workspace_axon_watch` | IDE agent turn, file edit, save, terminal |
| Wed | `workspace_axon_local` | Real repo git status, handoff if needed |
| Thu | DashPro child workspace | Monitors, connectors rail, tunnel status |
| Fri | Mixed | Full Access agent run, voice cockpit, mobile compact viewport |

### End-of-week criteria

- [ ] Zero unplanned `:7734` sessions OR each logged with blocker ID
- [ ] No data corruption in control-plane SQLite (runs, chat, vault)
- [ ] Operator confirms KAIRO/briefing rhythm acceptable on `:4173`
- [ ] Weekly note in audit log: shipped slice, confusion, next slice

**Phase E exit gate:** all end-of-week criteria checked + debt gate still clear.

---

## Phase F — Retirement sign-off

**Goal:** Operator explicitly accepts discards and reassesses retirement blockers.

| ID | Action | Gate |
|----|--------|------|
| F1 | Complete ack boxes in `docs/PHASE_G5_INTENTIONAL_DISCARDS.md` | Both sign-off checkboxes checked |
| F2 | Re-run blocker table in `docs/PHASE_G6_RETIREMENT_READINESS.md` § G6.1 | Evidence updated |
| F3 | `npm run verify:signal-parity-matrix` | PASS |
| F4 | `npm run verify:retirement-readiness` (TEST-17) | PASS (requires F1 + Phase E) |
| F5 | Operator review in `docs/CUTOVER_DECISION.md` | Human sign-off |
| F6 | E6 items in `docs/TRANSITION_PHASE_E_TODO.md` | Only if F5 approves |

**Phase F does not auto-retire axon-local.** TEST-17 PASS triggers operator review only.

### Rollback triggers (immediate `:7734`)

| Trigger | Action |
|---------|--------|
| Agent run loses file edits or corrupts workspace | Rollback; file G3/cli_runtime bug |
| Vault unlock blocks all LLM runs | Rollback; G1/G2 regression |
| Silent wrong run phase (stop doesn't stop) | Rollback; run-state truth bug |
| Child-project incident due to missing connector | Rollback for that project; log inventory ID |
| Operator judgment: `:4173` less trustworthy than `:7734` | Rollback; reprioritize slice |

Rollback procedure: `docs/PHASE_G6_RETIREMENT_READINESS.md` § G6.3.

---

## Explicit deferrals (do not start until Phase F exit)

| Item | Reason | Fallback |
|------|--------|----------|
| OP-C6 wake word | Requires proven PTT loop first | Typed + PTT only |
| G4.2 WhatsApp Web monitor | Bounded slice not shipped | `:7734` for DashPro WhatsApp |
| OP-V1g KAIRO mobile shell | Depends on OP-C4/C5 converse API | Desktop `:4173` |
| Electron desktop shell | Browser-only contract | Playwright + browser |
| Full `npm run verify` in TEST-3/9 step 5 | Scoped bundles until triage | Use bundle scripts |

---

## Agent session checklist (IDE Full Access turns)

When executing build slices in IDE Agent mode:

1. Read this plan — identify current phase and slice ID.
2. Confirm debt gate (Phase B) before feature work.
3. Implement **only** the active slice; no drive-by refactors.
4. Add or extend focused tests in the same slice.
5. Run the slice gate from the table above.
6. Append a one-line note to the relevant doc append log (audit log or parent plan).
7. Summarize what changed for the operator in plain language.

---

## Implementation order (locked)

```text
Phase A (baseline)
  → Phase B (hygiene O1–O5 closeout + debt clear)
    → Phase C (OP-C1 → C5 conversation loop)
      → Phase D (OP-B6e, OP-V1f, OP-B4, OP-B3 polish)
        → Phase E (G6 dry-run week — runs parallel to C/D if debt gate clear)
          → Phase F (G5.4 acks + retirement readiness)
```

**Parallel rule:** Phase E daily ritual runs alongside C/D **only when** the debt
gate is clear. If debt returns, pause C/D and return to Phase B.

---

## Append log

### 2026-07-11 — C6 (V5+V9) narration plumbing + settings copy

- Collapsed duplicate `shouldNarrateAgentEvent` branches; bookends only for
  minimal and conversational (tool/edit/thinking milestones stay silent here).
- Confirmed shell gates with `shouldNarrateAgentEvent` before `/api/kairo/speak`.
- Kept backend tool/edit fallback pools for later opt-in tool narration.
- Settings hints now match real behavior (start/done/alerts + one thinking line;
  conversational = polished phrasing, not per-tool chatter).
- Gate: `kairo-narration-policy.test.ts` PASS.
- **Next:** C7 (V1+V4+V6) honest mode labels, persona parity for thinking,
  error/fallback narration.

### 2026-07-09 — OP-C4 execute-tier confirm landed

- Server: `command_requires_confirmation()` + `requires_confirmation` on converse payload.
- Client: `shouldAutoDispatchConverseCommand` respects confirmation flag; yes-follow-up dispatches.
- UX: markdown workspace links, image attachment lightbox, galaxy workspace focus on nav intents.
- Gates green: kairo conversation pytest, vitest policy/intents/markdown, production-operator build.
- **Next:** C6 narration plumbing; debt gate stays clear (B1 dry-run: 0 stale runs).

### 2026-07-10 — OP-C5 turn memory + model picker

- Extracted `app/kairo/turn_memory.py` + `context_pack_cache.py`; lowered `kairo_conversation.py` ratchet to 697.
- Pack workspace falls back to `entity.target_workspace_id`; top-signal remember uses resolved pack workspace.
- Client: converse-first for handoff phrases; AgentDock model picker honors available non-composer catalog picks.
- Gates: `tests.test_kairo_conversation`, cursor-catalog-view + handoff-order vitest.

### 2026-07-09 — Locked execution plan published

- Consolidated G6 dry-run, hygiene O1–O5, OP-C, and brain polish into one ordered checklist.
- Debt gate enforced: 35 `review_ready` + 9 zombie `executing` block feature slices until B1 clears.
- Next active slice: **Phase A** baseline, then **Phase B1** cleanup.
- G5.4 operator acks remain human-only (Phase F1).

### 2026-07-09 — KAIRO voice + context/memory plan added

- Published `KAIRO_VOICE_IMPROVEMENT_PLAN.md` from Vaxon narration audit (11 gaps).
- Extended Phase C with C6–C12: narration hardening (V1–V9), session persistence (M1–M2),
  cross-channel memory (M3–M6), agent continuation (M4).
- Root issues: conversational mode oversells behavior; in-memory turn memory lost on restart;
  IDE agent does not inherit KAIRO conversation context.
