# CI, merge workflow, and worker agents

**Updated:** 2026-07-29

This chapter explains how Axon-X lands code through GitHub CI, how that relates
to the `dev` branch, and how **company employee agents** (the roster in IDE /
Mission Control) work — including how to tell whether they are actually running
and how good the automation is today.

**Related:** [`docs/CI_GATES.md`](../CI_GATES.md), [`docs/planning/EXECUTION_PLAN.md`](../planning/EXECUTION_PLAN.md),
[`recent-operator-features.md`](recent-operator-features.md)

---

## Names — do not confuse these

| Name | What it is |
|------|------------|
| **Axon-X Fast Gate** | GitHub Actions workflow (`.github/workflows/fast-gate.yml`) — automated tests on every push and PR |
| **GitHub → Agents tab** | GitHub product UI (Copilot / cloud agents). **Not** the Axon company roster |
| **Company roster / employee agents** | Config-driven roles (`Night Watch`, `Shell Craft`, …) in `config/workspace-agents.json` — continuous workers on a schedule |
| **Lane B / IDE agent** | Cursor CLI agent runs you start from the IDE composer (operator-driven) |
| **Cursor worker-server** | Internal Cursor subprocess; not an Axon employee by itself |

---

## CI and merge — how it works

### Integration truth

| Branch | Role |
|--------|------|
| **`dev`** | Integration branch. Protected on GitHub — **`fast-gate` must pass** before merge |
| **`feat/*`** | One feature slice per branch (e.g. `feat/operator-console`) |
| **`master`** | Legacy default; **not** the day-to-day Axon-X integration target |

Day-to-day console work targets **`dev`** via pull request. Do not camp on
`master` for operator-console slices.

### What triggers CI

Workflow: **Axon-X Fast Gate** (`.github/workflows/fast-gate.yml`)

Runs on:

- every **push** to any branch
- every **pull_request** (open, sync, reopen)

In the GitHub UI: **Actions** → workflow runs show green ✓ or red ✗. A PR also
shows the same check on the PR page.

### Poll Fast Gate from the terminal (required after every push)

Agents and operators should **not** wait for someone to notice a red run:

```bash
./scripts/ops/watch-fast-gate.sh
# or follow a known run id:
./scripts/ops/watch-fast-gate.sh 29925529734
```

On failure:

```bash
gh run view --log-failed
# Typical Fast Gate early fail: file-size ratchets in scripts/guardrails/hotspot_budgets.json
```

**Axon-X company ownership:** Rowan (watcher) + Mira (Lead) own Fast Gate for
`workspace_axon_watch`. Quinn (integrations) supports Actions wiring.

### What Fast Gate runs (~2–3 minutes)

1. **`npm run verify:contracts`** — shared types, control-plane/watch contract
   unit tests, file-size ratchets
2. **`npm run verify:hotspot-changes`** — critical hotspots must shrink or stay
   within budget when changed (PR compares against base branch)
3. **`npm run verify:console-web`** — Vue typecheck, full Vitest suite, production build
4. **`scripts/verify/all.py --strict-pending`** — import boundaries, DTO budgets,
   ADR governance, latency scaffold

If any step fails, the run is red and **`dev` cannot merge** that PR until fixed.

### Operator merge workflow

```text
feat/my-slice  →  push  →  open PR to dev  →  fast-gate green  →  merge  →  git pull origin dev
```

Step by step:

1. **Work on a feature branch** (not directly on `dev`).
2. **Commit focused slices** — one concern per PR when possible (worker scheduler
   separate from IDE chrome, separate from connector parity).
3. **Push** the branch (`git push -u origin feat/my-slice`).
4. **Open a PR** to `dev` (`gh pr create --base dev --head feat/my-slice`).
5. **Wait for `fast-gate`** — green on the PR (not only on an earlier push).
6. **Merge** when green (GitHub UI or `gh pr merge`).
7. **Sync locally:** `git fetch origin dev && git checkout feat/my-slice && git merge origin/dev` (or rebase per team habit).

**Important:** A green check on an old push does **not** guarantee the open PR
is green. Always read the check on the **PR** itself.

### Local preflight (before you push)

```bash
npm run verify:preflight   # via scripts/sc on commit — blocks bad commits locally
npm run verify:contracts   # fastest backend + ratchet signal
cd apps/console-web && npm run typecheck && npm run test
git status --short         # must contain no source changes or local runtime artifacts
```

Before opening a PR, fetch `dev`, integrate it on the feature branch, rerun the
preflight, and inspect the complete branch diff:

```bash
git fetch origin dev
git merge origin/dev
git diff --check
git diff --stat origin/dev...HEAD
```

Do not merge the feature branch directly into protected `dev`, force-push, or
hide a failing check. Local runtime artifacts (`control-plane.sqlite3`, debug
logs, shell completion dumps) are not source and must remain ignored.

Full local bundle (slower):

```bash
npm run verify
```

### Nightly gate (not on every PR)

Workflow: `.github/workflows/nightly-verify.yml` — live stack evidence. See
[`docs/CI_GATES.md`](../CI_GATES.md).

---

## Worker / employee agents — how they work

### What they are

Axon-X models each workspace as a **small company** with named employees
(lead, watcher, frontend, backend, integrations). Configuration lives in:

- **`config/workspace-agents.json`** — companies, roles, schedules, `owns` text
- **`services/control-plane/app/workspace_agents/`** — load config, derive status, scheduler

UI:

- **IDE → TEAM tab** (`IdeTeamPanel` → `CompanyRosterPanel`)
- **Talk / Assign** — pre-fills the IDE composer (operator-driven); does not by
  itself start a scheduled worker

### Schedules

| Schedule | Meaning |
|----------|---------|
| `on_demand` | No automatic shift (typical for **lead**) |
| `always_on` | Watcher-style; scheduler starts bounded shifts (e.g. **Night Watch**) |
| `continuous` | Specialist roles (frontend, backend, integrations) get recurring shifts |

Skipped from auto-schedule: `lead`, `overview_agent`.

### Scheduler loop (WA-1)

When the control plane starts (`services/control-plane/app/bootstrap.py`):

1. **`start_continuous_worker_scheduler()`** runs a background tick (default **every 45s**).
2. Each tick, for each `always_on` / `continuous` employee without an active
   role-tagged run, the scheduler:
   - **`create_run(..., employee_role=<role>)`** — run record in SQLite
   - **`dispatch_continuous_worker_run()`** — headless Lane B with a role-scoped
     prompt (`worker_prompt.py` → `worker_dispatch.py` → Cursor/Codex CLI)

Guards (so one restart cannot flood the fleet):

- **`MAX_STARTS_PER_TICK`** (6) — cap new starts per tick
- **`MAX_ACTIVE_EXECUTING`** (24) — skip new starts when executing debt is high
- Per-role gate — only one busy shift per `(workspace_id, employee_role)` at a time

### Environment knobs (`.env` / vault)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AXON_WATCH_WORKER_SCHEDULER` | `1` | Enable/disable scheduler |
| `AXON_WATCH_WORKER_SCHEDULER_DISPATCH` | `1` | Lane B dispatch after `create_run` |
| `AXON_WATCH_WORKER_SCHEDULER_INTERVAL_SECONDS` | `45` | Tick interval |
| `AXON_WATCH_WORKER_RUN_STALE_SECONDS` | `720` | Fail/cancel idle role-tagged shifts older than this |
| `AXON_WATCH_EMPLOYEE_RUN_RETENTION_PER_ROLE` | `8` | Keep this many finished role-tagged runs per workspace/role |
| `AXON_WATCH_REVIEW_READY_STALE_SECONDS` | `14400` | Auto-complete idle untagged `review_ready` checkpoints older than this |

Disable scheduler in tests: `AXON_WATCH_WORKER_SCHEDULER=0`.

Staffing file override: `AXON_WATCH_WORKSPACE_AGENTS_FILE` (path to JSON).

### Stale shifts and history retention

Hung role-tagged runs can block the next shift for that role. The control plane:

- Reaps idle employee runs on each scheduler tick and on startup
- Exposes `POST /api/runs/reconcile-stale` for an on-demand reap
- Drains finished employee-run history beyond the per-role retention window on
  startup / `POST /api/runs/prune-employee-history` (scheduler ticks prune in
  smaller batches so shifts stay responsive)
- Completes abandoned untagged `review_ready` checkpoints on startup, each
  scheduler tick, and `POST /api/runs/reconcile-review-ready` so briefing stays
  honest when review was never dismissed

Approval waits are never auto-completed or pruned. Fresh review checkpoints stay
until the idle TTL elapses.

---

## How to know if employee agents are working

### 1. Company roster (UI)

IDE mode → **TEAM** tab (or operator company panel). Each employee shows a status:
`idle`, `watching`, `executing`, `planning`, `verifying`, etc.

**Good sign:** specialists (`frontend`, `backend`, …) move to **`executing`**
when their shift is active, not only the lead mirroring any workspace run.

### 2. Mission Control / runs API

```bash
curl -sS http://127.0.0.1:8787/api/runs | python3 -c "
import sys, json
runs = json.load(sys.stdin)
if isinstance(runs, dict): runs = runs.get('runs', runs.get('items', []))
for r in runs:
    if r.get('employee_role') and r.get('phase') not in ('completed','failed','cancelled'):
        print(r['run_id'], r['workspace_id'], r['employee_role'], r['phase'], r.get('summary','')[:50])
"
```

**Good sign:**

- `employee_role` is set (`watcher`, `frontend`, …)
- `phase` is `executing` (or progresses to `completed` / `failed` with receipts)
- Summary mentions `continuous worker shift`

**Bad sign (phantom worker):** `executing` forever with **no** `cursor-agent`
process and **no** `runtime_dispatch` receipt on the run history.

### 3. Live CLI processes

```bash
pgrep -af 'cursor-agent.*agent --print' | head
```

You should see prompts like *"You are Shell Craft, the frontend employee for
workspace workspace_axon_watch…"* when dispatch is active.

### 4. Control plane health

```bash
./scripts/dev/check-health.sh
curl -sS http://127.0.0.1:8787/api/health
```

### 5. Agent shift digests (optional)

When agents write them, receipts live under **`docs/ops/agent-reports/`**
(untracked until committed). Use for human-readable "what this shift did."

### 6. Unit tests

```bash
PYTHONPATH=services/control-plane python3 -B -m unittest \
  tests.test_workspace_agent_scheduler \
  tests.test_workspace_worker_prompt \
  tests.test_workspace_agents -q
```

---

## How good are they? (honest assessment)

| Dimension | Today | Target |
|-----------|-------|--------|
| **Visibility** | Roster + runs show role and phase | Same, plus ranked coaching in briefing (SA-2) |
| **Autonomy** | Bounded scheduled shifts with role prompts | Continuous office cadence + checkpoint "meetings" |
| **Continuity** | One shift per role; tick every 45s | Stale reaper + handoff memory across shifts |
| **Quality of work** | Depends on Lane B + workspace scope; can edit/run in bound repo | Role-scoped playbooks (e.g. DashPro CI triage) |
| **Safety** | Debt caps, no auto-start for lead; dispatch uses controlled prompts | Autonomy ladder per workspace (`observe` → `full`) |

**They are real workers when:** Lane B dispatch is on, `cursor-agent` is running
with the role prompt, and runs complete or fail with receipts — not when the
scheduler only created an `executing` row.

**They are not yet:** a full autonomous company that manages its own PRs,
branches, or SA-2 coaching — that is the next execution slices on `dev`.

---

## Quick reference commands

```bash
# CI locally
npm run verify:contracts
npm run verify:console-web

# Open PR
gh pr create --base dev --head feat/my-slice --title "..." --body "..."

# PR checks
gh pr checks

# Worker scheduler tests
PYTHONPATH=services/control-plane python3 -B -m unittest tests.test_workspace_agent_scheduler -q

# Stale reconcile (when loaded on CP)
curl -X POST http://127.0.0.1:8787/api/runs/reconcile-stale
```

**PDF:** This chapter is bundled into `~/Desktop/Axon-X-How-To-Handbook.pdf` when you run
`./scripts/docs/build-howto-handbook-pdf.sh` (rebuild after handbook edits).
