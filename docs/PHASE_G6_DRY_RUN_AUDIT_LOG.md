# Phase G6 dry-run audit log

**Started:** 2026-07-07 (operator dry-run on `:4173`)  
**Auditor:** Cursor agent (automated snapshots + code review)  
**Stack:** axon-watch `dev` @ `98d04ea` (+ uncommitted operator UX slice)

---

## T0 snapshot (dry-run start)

### Stack health — GREEN

| Check | Result |
|-------|--------|
| `./scripts/dev/check-health.sh` | All endpoints OK |
| Console `:4173` | OK |
| Control plane `:8787` | OK, mode=bootstrap |
| Watch `:8788` | OK, connectors 2/4 ok |
| `verify:headed-browser-smoke` | PASS (5768 ms) |

### Run store — NEEDS ATTENTION

| Metric | Value |
|--------|-------|
| Total runs | 124 |
| `review_ready` | 36 (mostly `Git status`) |
| `executing` | 8–9 (zombie) |
| `completed` | 80 |

**By workspace (`review_ready`):** `workspace_axon_local` 26, `workspace_dashpro` 10, others vary.

**Zombie `executing` runs (`workspace_smoke`):** 8× `Git status` with `status=running`, `can_complete=null`.

**Root cause (verified on `run_32c7a4c95c78` history):**

1. Command executed successfully → `review_ready`
2. **`resume from review`** (acceptance test / operator) → back to `executing`
3. No follow-up work for one-shot commands → run **stuck forever** in `executing`

This explains KAIRO **ADVISE: "Resume Git status"** while Mission Control shows **STOP** (not COMPLETE).

### Briefing vs workspace scope

| Source | Message |
|--------|---------|
| Global briefing NOTICE | "36 runs are ready for operator review" |
| Workspace-scoped UI (after fix) | Should show count for *current* workspace only |

Uncommitted frontend fix scopes Mission Control headline; briefing API still global.

### Operator thread pollution

Persisted `workspace_axon_watch` operator thread: **111 messages** — not from manual operator use.

| Command | Count |
|---------|------:|
| `git status` | 19 |
| `check-health` | 6 |
| `run ./scripts/dev/check-health.sh` | 6 |
| `run npm test` | 6 |

**Source:** Live acceptance tests (`test_test0`, `test_test1`, `parity_d4`, `production-operator-smoke`) POST to `/api/chat/messages` against running dev stack. Runs persist in `.local/state/control-plane.sqlite3`.

### Inbox / signals

- 1× info: "Watch bootstrap ready" (expected in bootstrap mode)
- `degraded: false`, watch connected

---

## Bugs & misbehavior (ranked)

### P0 — Operator trust

1. **Resume trap on one-shot commands** — `resume from review` on `git_status` leaves run in `executing` with no exit. Tests and ADVISE encourage RESUME for git status.
2. **Run queue pollution** — Verification creates real persisted runs; UI looks broken on fresh open.
3. **Uncommitted fixes not in running CP** — `AUTO_COMPLETE_COMMAND_INTENTS` in `orchestration.py` may require control-plane restart to take effect.

### P1 — UX confusion

4. **Three surfaces, same data** — Mission Control queue + sidebar "Also waiting" + conversation command log.
5. **RESUME vs COMPLETE** — Quick guide (`operator-quick-guide.ts`) tells operators to RESUME for `review_ready`; wrong for read-only commands.
6. **Global vs workspace counts** — Briefing NOTICE counts all workspaces; queue is workspace-filtered.
7. **Primary run selection** — `selectPrimaryRun` prefers `review_ready` over stuck `executing`; stuck smoke runs may steal STOP affordance.

### P2 — Dry-run hygiene

8. **No verification run cleanup** — Acceptance tests should complete or cancel runs they create.
9. **IDE/OPERATOR draft sharing** — Fixed in uncommitted slice (`ideComposerDraft` split); needs commit + reload.
10. **Conversation dock role** — Fixed in uncommitted slice (compact + trim); still shows verification history until DB reset or "Complete all".

---

## OPERATOR mode improvement backlog (for post-audit slice)

### Must-do (intuitive operator loop)

| # | Change | Why |
|---|--------|-----|
| O1 | **Auto-complete read-only commands** (committed + CP restart) | Stops queue growth |
| O2 | **Block or no-op resume on one-shot intents** | Prevents zombie `executing` |
| O3 | **Update quick guide + ADVISE** — COMPLETE not RESUME for git/health/read | Matches mental model |
| O4 | **"Clear workspace queue"** one button + confirm | Clears verification debt |
| O5 | **Scope briefing NOTICE** to current workspace (API or client) | Fixes 36 vs 17 confusion |

### Should-do (clarity)

| # | Change | Why |
|---|--------|-----|
| O6 | **Single "Attention" surface** — collapse duplicate run lists | One queue, one action row |
| O7 | **Operator home when idle** — workspace picker + 3 suggested commands | Reduces "what do I do?" |
| O8 | **Separate verification workspace** or test DB | Stops polluting operator threads |
| O9 | **Conversation = last session only** (not full SQLite history) | Dock reads as chat, not log |
| O10 | **Mode pill explainer** — OPERATOR vs IDE one-liner in top bar | Dry-run operators camp in wrong mode |

### Nice-to-have

| # | Change |
|---|--------|
| O11 | Dev-only "Reset smoke state" script (truncate review_ready) |
| O12 | Run dedupe: same command within 60s attaches instead of new run |
| O13 | KAIRO speaks workspace-scoped notice only |

---

## Monitoring ticks

_Appended by `scripts/ops/g6-dry-run-monitor.sh` during dry-run._
### Tick 2026-07-07T15:39:40Z

- runs: 124 | phases: {'completed': 81, 'review_ready': 35, 'executing': 8}
- review_ready: 35 | executing: 8
- NOTICE: 35 runs are ready for operator review.
- ADVISE: Resume Git status.
- executing samples:
  - run_32c7a4c95c workspace_smoke Git status
  - run_4cc47c0e26 workspace_smoke Git status
  - run_7cabe5db71 workspace_smoke Git status
  - run_55a6c4d0dc workspace_smoke Git status
  - run_5bc9a1da90 workspace_smoke Git status

### Tick 2026-07-07T16:35:23Z

- runs: 132 | phases: {'completed': 88, 'review_ready': 35, 'executing': 9}
- review_ready: 35 | executing: 9
- NOTICE: 35 runs are ready for operator review.
- ADVISE: Resume Git status.
- executing samples:
  - run_32c7a4c95c workspace_smoke Git status
  - run_4cc47c0e26 workspace_smoke Git status
  - run_7cabe5db71 workspace_smoke Git status
  - run_55a6c4d0dc workspace_smoke Git status
  - run_5bc9a1da90 workspace_smoke Git status

### Tick 2026-07-07T20:45:48Z

- runs: 142 | phases: {'completed': 97, 'review_ready': 35, 'executing': 9, 'paused': 1}
- review_ready: 35 | executing: 9
- NOTICE: 35 runs are ready for operator review.
- ADVISE: Resume Git status.
- executing samples:
  - run_32c7a4c95c workspace_smoke Git status
  - run_4cc47c0e26 workspace_smoke Git status
  - run_7cabe5db71 workspace_smoke Git status
  - run_55a6c4d0dc workspace_smoke Git status
  - run_5bc9a1da90 workspace_smoke Git status

---

## Pivot plan (post dry-run)

Operator direction consolidated in [`docs/planning/OPERATOR_BRAIN_PIVOT.md`](planning/OPERATOR_BRAIN_PIVOT.md):

- Hygiene wave O1–O5 (auto-complete, zombie guard, scoped briefing)
- Second brain OP-B1–B5 (fleet grid, incident feed, demoted run strip, monitors, IDE handoff)
- **3D brain galaxy OP-B6** — visualization over `BrainGraphDTO`, not system truth
- Daily monitoring ritual via `scripts/ops/g6-dry-run-monitor.sh`

