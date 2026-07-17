# Axon-X How-To Handbook

**The master operator, teaching, debugging, and upgrade manual for Axon-X.**

This handbook is the **single front door** for working with **Axon-X** (`axon-watch`).
It is written for operators, reviewers, developers, and agents — in plain language first,
with copy-paste snippets, source pointers, and debugging steps when things go wrong.

Use it to:

- **Operate** the console day-to-day (`:4173`)
- **Teach** someone else how Axon-X works
- **Understand** the codebase without reading every file
- **Verify** changes before merge
- **Upgrade** the stack after pulls or dependency changes
- **Debug** when the UI, API, or tests misbehave

**Last verified:** 2026-07-06 — production operator at `:4173`, vault subscription auth + IDE composer catalog.

**Production URL:** http://127.0.0.1:4173 — [`docs/PRODUCTION_OPERATOR_SURFACE.md`](PRODUCTION_OPERATOR_SURFACE.md)

**Layered onboarding (shorter):** [`docs/AXON-X-STARTER-GUIDE.md`](AXON-X-STARTER-GUIDE.md)

---

## Table of Contents

1. [Quick Start](#quick-start) — first 5 minutes
2. [Handbook map](#handbook-map) — who reads what
3. [Operator manual](#operator-manual) — daily rituals
3.5. [Runtime auth, CLI, and tools](#runtime-auth-cli-and-tools) — Pro vs API key, native vs Cursor
4. [Teaching Axon-X](#teaching-axon-x-to-someone-else) — explain it to others
5. [Codebase in plain English](#codebase-in-plain-english) — what happens under the hood
6. [Source index](#source-index) — where truth lives
7. [Snippet cookbook](#snippet-cookbook) — copy-paste commands
8. [Terminology](#terminology-and-abbreviations)
9. [Architecture & repo layout](#what-axon-x-is) — structure and ownership
10. [Detailed setup](#detailed-setup-first-install) — first install
11. [Boot flow](#what-the-current-app-does-on-boot) — what loads on refresh
12. [Shell layout](#locked-shell-layout) — regions and modes
13. [Key files](#the-most-important-files-right-now) — start reading here
14. [Verification](#verification-commands) — gates and PASS/PENDING/FAIL
15. [Working patterns](#common-working-patterns) — how to add code safely
16. [Debugging playbook](#debugging-playbook) — step-by-step fixes
17. [Tips, hints & tricks](#tips-hints-and-tricks)
18. [Upgrading & updating](#upgrading-and-updating) — pulls, deps, planning sync
19. [Next slices](#what-a-good-next-slice-looks-like) — what to build next

---

## Handbook map

| Audience | Start here | Then read |
|---|---|---|
| **Operator (daily use)** | [Quick Start](#quick-start) | [Runtime auth, CLI, and tools](#runtime-auth-cli-and-tools), [Operator manual](#operator-manual) |
| **Teacher / reviewer** | [Teaching Axon-X](#teaching-axon-x-to-someone-else) | [Verification](#verification-commands), `docs/FINAL_PARITY_VERIFICATION.md` |
| **Developer** | [Codebase in plain English](#codebase-in-plain-english) | [Source index](#source-index), [Common working patterns](#common-working-patterns) |
| **Debugger** | [Debugging playbook](#debugging-playbook) | [Troubleshooting](#troubleshooting) |
| **Upgrader** | [Upgrading & updating](#upgrading-and-updating) | `./scripts/ops/sync_planning_mirror_to_axon_local.py` |

Shorter onboarding: [`docs/AXON-X-STARTER-GUIDE.md`](AXON-X-STARTER-GUIDE.md)

---

## Quick Start

This section is the living operator onboarding guide.

### Start the stack

```bash
cd /home/edp/axon-nvme/repos/axon-watch
./scripts/dev/up.sh
./scripts/dev/check-health.sh
```

Open **http://127.0.0.1:4173** and hard-refresh after upgrades (`Ctrl+Shift+R`).

### Pick a real workspace

The left sidebar should show **axon-watch** and **axon-local** (bound project
roots). Start with **axon-watch** for Axon-X development, or **axon-local** when
you need the legacy repo context.

Demo names like `workspace_nlp` are mock catalog entries — they are hidden when
real project bindings exist.

### Two modes — different jobs

Axon-X has two layout modes (top-right toggle). They are **not** two different apps;
they are two views over the same workspace, runs, and APIs.

| | **Operator mode** | **IDE mode** |
| --- | --- | --- |
| **Purpose** | Run oversight, signals, approvals, command execution | Files, editor, terminal, agent dock |
| **Center** | Mission control — run phase, live feed, resume/complete | Monaco editor + bottom terminal dock |
| **Left sidebar** | Workspaces + **Attention** (signals, inbox, receipts) | Explorer / search / git activity bar |
| **Right dock** | Conversation transcript + Command/KAIRO hero | Resizable agent dock (conversation + composer) |
| **Best for** | “What is running? What needs me? Run this command.” | “Edit files, use terminal, review code.” |
| **Input style** | **Exact commands** in the Command seam (see footer **Commands**) | Same command seam in agent dock + full editor/terminal |

**Operator mode** is the default production surface for day-to-day oversight.

**IDE mode** is for hands-on work in the bound repo (real `project_root` on disk).

Switch modes anytime — workspace selection, runs, and conversation thread persist.

### What you can do in Axon-X today (v1)

Real and verified today:

- Select **axon-watch** or **axon-local** workspace
- View **runtime summary**, **inbox signals**, and **KAIRO briefing** from live APIs
- Track **run phase** in mission control (stop/resume/review-ready flows)
- Send **supported commands** (not free-form chat) via the Command seam
- Run **git status** against the bound repo root
- **IDE mode**: open workspace files in Monaco, PTY terminal in repo root
- **Attention sidebar**: connector/signal/delivery visibility

Still thin or deferred (use axon-local `:7734` fallback if needed):

- General conversational chat (“Hi”, “explain this repo”)
- Full agent tool loop parity with classic Axon
- Child-project connectors and legacy integration surfaces
- Packaged desktop app / native notifications

### Supported commands (Operator mode)

The conversation/command seam accepts **exact commands** only. Natural language
will return “unsupported command”.

| Command | What it does |
| --- | --- |
| `health` / `api/health` | Probe control-plane health |
| `ls` / `list files` | List files in the workspace |
| `read README.md` / `cat notes.txt` | Read a workspace file |
| `git status` | Git status in the bound project root |
| `resume from review` | Resume the primary `review_ready` run |

In the UI: footer **Commands** button (Operator mode) opens the list and can prefill
the Command seam. Source of truth:
`apps/console-web/src/lib/operator-supported-commands.ts` (keep in sync with
`services/control-plane/app/chat/command_executor.py`).

### Typical first session

1. Open `:4173` → wait for boot overlay → shell loads
2. Left sidebar → select **axon-watch**
3. Operator mode → right dock → **Command** tab
4. Type `git status` → send → read agent receipt in **Conversation**
5. Center mission control shows run phase if a run was created
6. Toggle **IDE** → open `README.md`, use terminal in the real repo root
7. Left **Attention** → inspect signals when watch reports degraded summary

### When things look noisy

Dev SQLite may contain old smoke runs (“32 runs ready for review”). Reset if needed:

```bash
./scripts/dev/down.sh
rm -f .local/state/control-plane.sqlite3
./scripts/dev/up.sh
```

### Verify smoke

```bash
npm run verify:production-operator
```

### Understanding runs, review_ready, RESUME, and COMPLETE

**Analogy:** Axon-X is a **supervised assistant**, not a chat bot. When you send a
command like `read README.md` or `health`, the system starts a **run** (a tracked
job): do the work → show output in **Conversation** → **pause** at a checkpoint called
**review_ready**. That pause is intentional — you look at the result before anything
else happens.

| Button / action | Plain meaning | When to use it |
| --- | --- | --- |
| **COMPLETE RUN** | “I’m done — this job succeeded.” | One-shot commands (`read …`, `git status`, `health`) when output looks good |
| **RESUME RUN** | “I’ve reviewed it — keep this run going.” | Multi-step work, or when KAIRO **ADVISE** says to resume a named run |
| **Command → `resume from review`** | Same as RESUME for the **primary** paused run | When buttons are unclear; acts on one run at a time |
| **Left → Attention** | Signal inbox (bootstrap noise, delivery receipts) | When footer shows **SIGNALS: N ACTIVE** — usually informational in dev |

**“Phase is now review_ready. Review when ready.”** — not an error. The command
finished; Mission Control is asking you to **COMPLETE** (usual) or **RESUME** (if more
steps expected).

### “2 runs are ready for operator review” — what that means

This is a **count of paused jobs**, not a failure. Each command you ran (`health`,
`read README.md`, `git status`, …) can leave its own run sitting in **review_ready**
until you **COMPLETE** or **RESUME** it. **2 runs** = two unfinished checkpoints
(e.g. one Health run + one Read README run).

**What to do:**

1. **Center → Mission Control** — handles the **primary** (most recent) run via
   **RESUME RUN** / **COMPLETE RUN**.
2. **Right → KAIRO Briefing** — see **NOTICE** (the count) and **ADVISE** (suggested
   next click).
3. **Clear the backlog** — for each run you’re happy with, click **COMPLETE RUN**.
   Repeat until the notice says “No active runs” or only one remains.
4. **Dev reset** (optional) — wipe stale runs from smoke tests:

```bash
./scripts/dev/down.sh && rm -f .local/state/control-plane.sqlite3 && ./scripts/dev/up.sh
```

### KAIRO NOTICE / ADVISE / DECIDE — where to go

KAIRO Briefing (right dock → **KAIRO** tab, or footer **Open KAIRO Briefing**) is a
**short summary**, not a second app. It mirrors the same backend truth as Mission
Control and Attention.

| Label | Meaning | Where to act |
| --- | --- | --- |
| **NOTICE** | Headline (“2 runs are ready…”) | Read only — context |
| **ADVISE** | Suggested next step (e.g. “Resume Health.”) | Usually → **RESUME RUN** in center, or **COMPLETE RUN** if that job is done |
| **DECIDE** | What choice is waiting | Center buttons, or Attention for signals |
| **EXECUTE** | Concrete action phrase | Command tab, or the button ADVISE points to |

**Example:** ADVISE says **“Resume Health.”** → you previously ran `health` and that
run is paused → go to **Mission Control** → **RESUME RUN** (continues that run) or
**COMPLETE RUN** (closes it if you only wanted a one-time health check).

**Signals (e.g. “Bootstrap: runtime summary stale”)** in **Attention** are often
**expected in local dev** — watch/bootstrap scaffolding, not production outage. Review
them in **Left → Attention**; they do not block **COMPLETE RUN** unless an approval
gate is open.

### Bootstrap & signals — what to do

**Bootstrap** in Axon-X means the console and services are up, but some runtime
summary fields are still intentionally thin while watch/control-plane parity grows.
That is normal in local dev — not the same as “the app is broken.”

| What you see | What it means | What to do |
| --- | --- | --- |
| **Bootstrap: runtime summary stale** (Attention → Signals) | Watch is connected; summary assembly is bootstrap-thin | **Ignore**, tap **Details**, or hit **CLEAR** to acknowledge and hide bootstrap noise |
| **OBSERVE** chip on a signal | KAIRO watch mode: informational only | **No click action.** Read-only label. |
| **DELIVERED** chip | Delivery receipt was recorded | **No click action.** Read-only label. |
| **SIGNALS: N ACTIVE** (footer) | N open inbox signals | Open **Attention** or **Open Attention** from Mission Control — review, then return to Command |
| **IDLE** + bootstrap signal only | Nothing waiting on you | No run action required — optional signal review only |

**When bootstrap noise is OK:** local `./scripts/dev/up.sh`, watch healthy, no pending
approvals, runs complete normally.

**When to investigate:** approvals stuck open, runs won’t resume/complete, watch
disconnected in footer, or bootstrap signal persists **after** a production deploy
with full runtime summary expected.

See also [Tip 6: bootstrap-real vs feature-real](#tip-6-distinguish-bootstrap-real-from-feature-real).

### Run names — what you see in the UI

Every command creates a **run** with two identifiers:

| What you see | Meaning |
| --- | --- |
| **Health check**, **Read README.md**, **Git status** | Friendly **task name** (from your command) |
| **#cdb931** (6 characters) | Short **run ref** — internal tracking only; you rarely need the full `run_…` id |

Old runs stored raw command text (`health`, `git status`); the UI **humanizes** those labels.
KAIRO **ADVISE** uses the same friendly names (e.g. “Resume Health check.” not “Resume health.”).

When **2+ paused tasks** appear, Mission Control lists each friendly name — click **COMPLETE RUN**
for the current one, repeat until the queue clears.

## Runtime auth, CLI, and tools

This section explains how Axon-X authenticates agent runtimes, when you need
secrets in **/vault**, and when Axon uses its own executors vs external CLIs.

Official Cursor CLI reference:
[Cursor CLI authentication](https://cursor.com/docs/cli/reference/authentication)

### Two auth paths for Cursor (Pro / daily use vs headless)

| Path | When to use | What you do | Vault key required? |
| --- | --- | --- | --- |
| **CLI subscription (recommended)** | Daily operator work on your machine with Cursor Pro/Team | Run `cursor agent login` once on the **host**; verify with `cursor agent status` | **No** — `CURSOR_API_KEY` is optional |
| **API key (headless / CI)** | Servers without browser, automation, cloud agents | Generate key in **Cursor Dashboard → Integrations → API Keys**; store as `CURSOR_API_KEY` in /vault or shell env | **Yes** (or shell env) |

Axon-X probes subscription auth live:

- **Vault consumer** (`/vault` → Consumer readiness): marks **Cursor CLI runtime** **Ready** when `cursor agent status` shows a logged-in account, even with zero vault keys.
- **Control plane** (`GET /api/runtime/status`, `GET /api/runtime/cursor/status`): same probe; composer shows account + auth method.
- **Dispatch**: if subscription is active, control-plane **strips** `CURSOR_API_KEY` from the subprocess env to avoid auth conflicts (browser login and API key are alternate paths per Cursor docs).

**Pro without vault key:** if `cursor agent status` prints `Logged in as …@…` and vault search shows no `CURSOR_API_KEY`, you are on the **subscription path** — correct for daily Pro use.

### Codex / OpenAI auth

| Path | Setup |
| --- | --- |
| **Codex CLI login** | `codex login` on the host; vault consumer probes `codex login status` |
| **API keys in vault** | `CODEX_API_KEY` or `OPENAI_API_KEY` in /vault (either satisfies the codex consumer) |

### Vault consumers vs runtime dispatch

**Consumers** are readiness labels for operators — they never expose secret values.

| Consumer | Ready when | Optional / fallback |
| --- | --- | --- |
| `cursor_runtime` | CLI subscription **or** `CURSOR_API_KEY` in vault | API key only needed for headless |
| `codex_runtime` | `codex login` **or** Codex/OpenAI vault keys | |
| `openai_provider` | `OPENAI_API_KEY` in vault | Direct OpenAI fallback |
| DashPro monitor consumers | Required monitor keys in vault/import | |

Source: `services/axon-watch/app/vault/snapshot.py`, `cli_runtime_probe.py`

**Runtime dispatch** (actually running a model) lives in the control-plane:

- `services/control-plane/app/cli_runtime/catalog.py` — auth probes, ready flags
- `services/control-plane/app/cli_runtime/router.py` — picks binary, env, retry without API key on oauth
- `services/control-plane/app/cli_runtime/vault_keys.py` — merges unlocked vault keys into runtime context

### Native Axon tools vs Cursor CLI

Axon-X has **two execution lanes** — do not mix them when debugging.

| Surface | Lane | Executor | Tools |
| --- | --- | --- | --- |
| **Operator mode** → Command seam | **Lane A — Command** | Axon `command_executor.py` | Exact commands only (`health`, `git status`, `read …`) — **Axon native** |
| **IDE mode** → Agent dock composer | **Lane B — Ask / Plan / Agent** | Cursor CLI subprocess (`cursor agent …`) | Cursor model + consultative prompt; **not** full Cursor IDE agent tools yet |
| **Future (G3.5+)** | MCP registry | Planned wiring | Static registry exists; **not** connected to dispatch today |

**When to use native Axon tools:** Operator oversight, deterministic repo commands, health checks, file reads — anything in the [supported commands](#supported-commands-operator-mode) table.

**When Cursor CLI runs:** IDE composer messages in Ask, Plan, or Agent mode with runtime target **Cursor CLI (local)**. Streaming (SSE) applies to this lane when `AXON_WATCH_LANE_B_STREAMING=1` (default).

**Composer modes (IDE dock):**

| Mode | Cursor CLI flag | Behavior today |
| --- | --- | --- |
| **Ask** | `--mode ask` | Read-only style answers |
| **Plan** | `--mode plan` | Step mapping before execution |
| **Agent** | Default consultative; **Full Access** in composer → approval → Cursor `--mode agent` / Codex workspace-write | `execution_access: full` + G3.3 approval gate |

### Choosing runtime target and model

Open the **model picker** (⚡ chip) in the IDE agent dock:

1. **Runtime target** — `Cursor CLI (local)`, `Codex CLI (local)`, or cloud placeholders. Preference persists in shell local storage via `shell.setSelectedRuntimeTarget`.
2. **Auto toggle** — when ON, Cursor picks the best model per request (no `--model` flag). When OFF, your pinned catalog model is passed to the CLI.
3. **Add models** — browse live output of `cursor agent --list-models` (cached ~5 min). Badges like **Fast** / **High** come from CLI labels when present.
4. **Auth line** — shows `CLI subscription · you@domain` or vault/API-key status; **Open Vault** only when auth is actually blocked (vault locked or missing keys **and** CLI not signed in).

Environment overrides:

| Variable | Purpose |
| --- | --- |
| `AXON_WATCH_CURSOR_CLI_PATH` | Non-default `cursor` binary path |
| `AXON_WATCH_CODEX_CLI_PATH` | Non-default `codex` binary path |
| `AXON_WATCH_LANE_B_STREAMING` | `1` (default) SSE streaming for IDE composer; `0` in tests |

API endpoints:

- `GET /api/runtime/status` — all targets + vault posture
- `GET /api/runtime/cursor/status?force_refresh=1` — Cursor auth + live model catalog
- `GET /api/vault/status` — consumer readiness (axon-watch service)

### Troubleshooting auth

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Vault shows **Missing: CURSOR_API_KEY** but CLI is logged in | Stale UI or old snapshot | Refresh /vault; consumer should show **CLI subscription · …** |
| Composer says invalid API key | Stale `CURSOR_API_KEY` in vault **or** shell env conflicting with subscription | Remove bad key from vault; unset shell `CURSOR_API_KEY`; restart control-plane |
| `cursor agent status` → not logged in | No subscription session on host | `cursor agent login` |
| Runtime ready but dispatch fails | Wrong binary or model id | Check `AXON_WATCH_CURSOR_CLI_PATH`; pick **Auto** or a model from live catalog |
| **Open Vault** when Pro works | Should not show if oauth ready | Hard-refresh; verify `GET /api/runtime/status` shows `ready: true` |
| **Out of usage** / rate limit from Cursor | Current CLI account hit subscription quota | Switch accounts (below) or use **Auto** / another model; admin may need to raise team limits |

### Switch Cursor subscription account (logout → login)

When the agent reports **out of usage** or you need a different Pro/Team account on this machine:

```bash
# 1. Sign out (clears stored CLI session on this host)
cursor agent logout

# 2. Confirm logged out
cursor agent status   # should say not logged in / auth required

# 3. Sign in with the other Cursor account (opens browser)
cursor agent login

# 4. Verify the new account
cursor agent status   # expect: Logged in as other@domain
```

Headless terminal (no browser auto-open):

```bash
NO_OPEN_BROWSER=1 cursor agent login
# Open the printed URL manually in a browser logged into the target account
```

After switching:

1. Refresh **/vault** → Cursor consumer should show the new **CLI subscription · email**
2. Hard-refresh `:4173` or reopen the model picker (forces runtime status refresh)
3. Retry IDE composer — old thread errors are from the prior account/session; start a new turn

**Note:** Axon-X does not store Cursor passwords. Logout/login only affects the **host Cursor CLI** session. Vault `CURSOR_API_KEY` (if present) is separate — remove or update it if you switch to API-key auth instead.

Quick host checks:

```bash
cursor agent status          # expect: Logged in as …
echo "${CURSOR_API_KEY:+set}" # empty = good for Pro path
curl -s http://127.0.0.1:8787/api/runtime/cursor/status | python3 -m json.tool
```

## Terminology And Abbreviations

Use this glossary when reading plans, ADRs, code, or agent summaries.

| Term | Meaning |
| --- | --- |
| **ADR** | Architecture Decision Record — a numbered, immutable write-up of a significant technical or process choice. Accepted ADRs live in `docs/adr/`. Do not rewrite them; supersede with a new ADR instead. |
| **Axon-X** | User-facing product name for the next-generation operator console. |
| **axon-watch** | Internal repo folder and npm workspace name. Legacy naming; not the product label shown to operators. |
| **axon-local** | The current production Axon app repo (port **7734**). Planning for Axon-X still lives here under `Plans/Axon-Watch/`. |
| **Bootstrap** | Early boot / dev scaffolding state — services run, but some DTO fields (runtime summary depth, signal richness) are intentionally thin until parity slices land. Signals like `Bootstrap: runtime summary stale` are **expected locally**, not production outages. |
| **Briefing seam** | `GET /api/briefing` returns canonical `OperatorBriefing`. The shell loads it at bootstrap and projects that data across the right dock: approvals, signals, and the KAIRO briefing card all read from the same briefing/runtime truth. Approval mutations stay on the run approval seam. See `docs/contracts/BRIEFING-SEAM.md`. |
| **Control plane** | FastAPI service on port **8787** that owns run truth, runtime summary, inbox projection, workspaces list, and briefing. |
| **Console-web / shell** | Vue 3 frontend on port **4173** — the visible Axon-X UI. |
| **Contract / shared contract** | Canonical TypeScript types and JSON fixtures in `packages/shared-types/`. Frontend and backend must agree here first. |
| **Coordinator lane** | Single owner of serial-only semantics during multi-agent work. See `docs/MULTITASK-LANES.md`. |
| **DTO** | Data Transfer Object — a typed payload shape exchanged between services or UI layers (for example `RuntimeSummary`, `RunRecord`). |
| **Fitness function** | An automated check that guards architecture or performance (dependency direction, DTO size budgets, latency thresholds). |
| **Frozen planning bundle** | The locked docs under `axon-local/Plans/Axon-Watch/`. Implementation must not silently drift from these. |
| **KAIRO** | Knowledge-Augmented Intelligence for Response and Oversight — operator-presence layer (watching, advising, interrupting, executing with receipts). **NOTICE / ADVISE / DECIDE** in the KAIRO Briefing panel are rhythm labels from `GET /api/briefing` — suggested reading, not separate commands. See Quick Start → *KAIRO NOTICE / ADVISE*. |
| **Lane A/B/C/D** | Parallel implementation ownership areas defined in `docs/MULTITASK-LANES.md` (watch, shell, control-plane, dev/verify). |
| **Monaco host** | In-browser code editor surface (`EditorHost.vue`). Loads workspace files on disk (README.md, notes.txt) plus read-only DTO overview tabs. |
| **Parity ledger** | Checklist of behaviors Axon-X must eventually match from current Axon. Lives in frozen planning. |
| **Run / run record** | Canonical execution unit with `phase`, `status`, capability flags, and transition history. |
| **Run phase** | High-level lifecycle stage (`queued`, `starting`, `executing`, `awaiting_approval`, `review_ready`, `completed`, etc.). Defined in frozen `run-state.md`. |
| **Runtime summary** | Boot-critical DTO at `GET /api/runtime/summary` — identity, watch connection, active runs, approvals snapshot. |
| **Signal / inbox item** | Watch-produced event surfaced through control-plane `GET /api/inbox`. |
| **Thin slice** | A small, verifiable vertical increment — one owned behavior with tests, not a broad rewrite. |
| **Watch service** | FastAPI service on port **8788** that produces canonical signals; control-plane projects them into inbox/runtime summary. |
| **xterm host** | In-browser terminal surface (`TerminalHost.vue`) attached to a **backend PTY session** via `WS /api/workspaces/{workspace_id}/terminal`. Runs real shell commands in a workspace-scoped directory under `.local/workspaces/` (override with `AXON_WATCH_WORKSPACE_ROOT`). |
| **Workspace** | Logical operator context keyed by `workspace_id`. Today the API returns IDs only; rich catalog metadata is deferred. |

### Two repos, two apps

Do not confuse these:

| | **axon-local** (current Axon) | **axon-watch** (Axon-X) |
| --- | --- | --- |
| Default URL | `http://127.0.0.1:7734` (fallback) | `http://127.0.0.1:4173` (**production operator**) |
| Start command | `./start.sh` from axon-local | `./scripts/dev/up.sh` from axon-watch |
| Status | Legacy daily-driver / fallback | Primary operator console (v1) |
| Relationship | Source of parity targets and frozen plans | Implementation target for modernization |

## What Axon-X Is

**Axon-X** is the next-generation Axon console and operator environment.

The code lives in the `axon-watch` repo folder for now. That folder name is
legacy/internal; the product name is **Axon-X**.

The target product combines:

- an IDE-style shell
- a control plane
- a dedicated watcher service

The implementation repo is here:

- `/home/edp/axon-nvme/repos/axon-watch`

The frozen planning source-of-truth still lives here:

- `/home/edp/axon-nvme/repos/axon-local/Plans/Axon-Watch/`

Important rule:

- read plans from `axon-local`
- implement in `axon-watch`

Do not casually move back and forth inventing new semantics in both places.

## What State The Repo Is In Right Now

The repo is in an early but real bootstrap state.

What already exists:

- repo scaffold
- `console-web` shell skeleton
- `control-plane` FastAPI bootstrap service
- `axon-watch` FastAPI bootstrap service
- shared contract package
- verification harness
- health and readiness scripts

What is already real:

- root workspace scripts
- service startup/shutdown flow
- `/api/runtime/summary`, `/api/inbox`, `/api/runs`, and `/api/briefing` routes in the control plane
- shared contract types under `packages/shared-types/`
- shell consumption of canonical runtime summary, inbox, and run DTOs
- thin Monaco and xterm host surfaces in `console-web`

What is still intentionally thin or deferred:

- full signal production and deeper ranking beyond current inbox rule stack
- deep watch summary logic
- performance evidence for all budgets

What is now real in the thin slice (verified 2026-07-04):

- run create/complete/stop/resume lifecycle
- explicit approval boundary (`requires_approval`, approve/reject)
- review-ready entry, completion, and follow-up resume path
- SQLite-backed run persistence (survives control-plane restart)
- operator briefing loaded at bootstrap and rendered in the right dock (`BriefingPanel.vue`)
- two watch-produced inbox signals with multi-factor ranking (severity, recency,
  unresolved duration via `created_at`, status, action-type, workspace priority)
- workspace list API and shell workspace selector (IDs only)
- the shell is split into `TopBar`, `LeftSidebar`, `CenterWorkbench`,
  `RightDock`, and `StatusBar` regions with mockup-shell chrome
- Monaco host bound to canonical DTO documents and **workspace files on disk**
  with a nested explorer tree, lazy file loading, new-file creation, and active-file rename
- backend PTY terminal attachment for the selected workspace (real shell I/O via WebSocket)
- workspace-scoped conversation rehydration: `GET /api/workspaces/{workspace_id}/chat/thread`
  plus existing thread history read reloads the Conversation seam after page refresh.
  When no thread exists yet, the lookup returns HTTP 200 with null `thread_id` (not 404).

**Workspace IDs (operator vs catalog):**

- **Operator shell** uses `MOCKUP_WORKSPACE_IDS` only (`workspace_smoke`, `workspace_recsys`,
  …). `mergeMockupWorkspaceCatalog()` trims API extras so `currentWorkspace` is always
  sidebar-visible.
- **Control-plane catalog** may still list fixture defaults (`workspace_alpha`,
  `workspace_bootstrap`) and run/inbox IDs for tests and API consumers; the shell does
  not select those as `currentWorkspace`.
- Bootstrap picks workspace deterministically: active run workspace (when visible) →
  `workspace_smoke` default → first mockup workspace.

Manual acceptance for reload-safe chat (use **`workspace_smoke`**):

1. `./scripts/dev/up.sh`
2. Open `http://127.0.0.1:4173`
3. Confirm **`workspace_smoke`** is selected (or select it)
4. Post a command in the Command seam
5. Hard reload the page
6. Conversation should rehydrate automatically for the same workspace when an active run
   or default bootstrap applies; if needed, re-select **`workspace_smoke`**

API-only check (any valid catalog ID):

```bash
curl -s http://127.0.0.1:8787/api/workspaces/workspace_smoke/chat/thread
curl -s http://127.0.0.1:8787/api/chat/threads/<thread_id>/history
```

What is **not** real yet despite similar-sounding names:

- **Full KAIRO operator presence** — the current shell has visual scaffolding,
  but spoken alerts, persona settings, and richer operator-presence behavior are
  still planned in axon-local docs
- **Full parity with axon-local** — intentional; see parity ledger for gaps

So this repo is not a fake mockup, but it is also not feature-complete or a
drop-in replacement for the current Axon UI.

## Source Of Truth Rules

When you are unsure what something should mean, check the planning bundle.

The most important frozen planning docs are:

- `PRODUCT.md`
- `ARCHITECTURE.md`
- `UI_SPEC.md`
- `UI_COMPOSITION_SPEC.md`
- `UI_VISUAL_DIRECTION.md`
- `UI_REFERENCE_ARCHETYPES.md`
- `run-state.md`
- `runtime-summary.md`
- `signal-events.md`
- `watch-api.md`
- `control-api.md`
- `PARITY_LEDGER.md`
- `FITNESS_FUNCTIONS.md`
- `TRANSITION_ARCHITECTURE.md`
- `CONTRACT_TESTING_SPEC.md`

### Things you must not redefine casually

These are serial-only semantics and should not drift:

- canonical run phases
- runtime summary vocabulary
- signal identity, severity, and status
- approval semantics
- transition seams and rollback rules
- parity acceptance rules

If the plan seems wrong or insufficient:

- do not silently change it
- raise a proposed amendment instead

## Repo Layout

Top-level structure:

```text
axon-watch/
  apps/
    console-web/
  services/
    control-plane/
    axon-watch/
  packages/
    shared-types/
  docs/
  scripts/
    dev/
    verify/
  infra/
  tests/
```

### What each part owns

#### `apps/console-web/`

Owns the integrated shell:

- topbar
- left sidebar
- center workbench (including the embedded terminal dock)
- right dock
- status bar

It should consume canonical contracts, not invent backend truth.

#### `services/control-plane/`

Owns interactive backend responsibilities such as:

- UI-facing health/readiness
- runtime summary assembly
- later run-state, approvals, and workspace orchestration

#### `services/axon-watch/`

Owns watcher responsibilities such as:

- monitoring loops
- watch health/readiness
- later signal production
- later inbox/signal summaries

#### `packages/shared-types/`

Owns canonical shared contract types.

This is one of the most important directories in the repo.

If frontend and backend disagree about what a thing means, the fix should start
here, not in ad hoc local types.

#### `scripts/dev/`

Owns local run helpers:

- start
- stop
- health checks

#### `scripts/verify/`

Owns cheap, repeatable verification:

- dependency direction checks
- DTO size checks
- ADR governance checks
- latency-budget check scaffolding

## The Current Architecture In Plain English

Think of the new app as three cooperating parts:

1. the shell the user sees
2. the control plane that serves user-facing APIs
3. the watcher service that will eventually observe and normalize signals

The current implementation is following a thin-slice path:

- bootstrap the shell and services first
- land canonical contracts early
- add real endpoints against those contracts
- then deepen behavior

This is deliberate.

It avoids:

- giant rewrites
- hidden semantic drift
- UI and backend inventing different meanings

## Detailed setup (first install)

## 1. Go to the repo

```bash
cd /home/edp/axon-nvme/repos/axon-watch
```

## 2. Install JavaScript dependencies

```bash
npm install
```

This is important because root workspace commands now rely on npm workspaces.

## 3. Review environment defaults

Default values are provided in:

- `.env.example`

If you need custom ports or local paths:

```bash
cp .env.example .env
```

Then edit `.env` as needed.

## 4. Start the local stack

```bash
./scripts/dev/up.sh
```

`up.sh` does not report success until all three services are actually reachable.

This starts:

- `console-web`
- `control-plane`
- `axon-watch`

Important startup contract:

- ports are fixed by `.env` / `.env.example`
- startup fails fast if `4173`, `8787`, or `8788` is already in use
- startup rolls back partial processes if readiness fails
- services stay detached after the launching shell exits

## 5. Check health

```bash
./scripts/dev/check-health.sh
```

Expected endpoints:

- console web: `http://127.0.0.1:4173`
- control plane health: `http://127.0.0.1:8787/api/health`
- watch health: `http://127.0.0.1:8788/internal/watch/health`
- briefing: `http://127.0.0.1:8787/api/briefing` (also loaded by the shell at bootstrap)
- runtime summary: `http://127.0.0.1:8787/api/runtime/summary`
- inbox: `http://127.0.0.1:8787/api/inbox`
- runs: `http://127.0.0.1:8787/api/runs`
- workspaces: `http://127.0.0.1:8787/api/workspaces`

`check-health.sh` also probes `/api/workspaces`.

## 6. Stop the stack

```bash
./scripts/dev/down.sh
```

## What The Current App Does On Boot

Right now, the shell boots and loads five control-plane seams in parallel.

That flow looks like this:

1. `apps/console-web/src/main.ts` creates the Vue app
2. the shell store initializes
3. `loadBootstrapData()` is called
4. the frontend fetches `/api/runtime/summary`, `/api/inbox`, and `/api/briefing`
5. workspaces and runs load sequentially; `resolveBootstrapWorkspaceId()` sets
   `currentWorkspace` (active run workspace when sidebar-visible, else `workspace_smoke`)
6. workspace files and chat thread history load for that workspace
7. the shell renders topbar context, workspace state, editor/terminal workbench,
   right-dock seams, and status bar truth strips

Important limitations:

- **Operator workspace list** — shell and sidebar share the same `MOCKUP_WORKSPACE_IDS`
  catalog; catalog-only IDs such as `workspace_alpha` remain API-visible but are not
  selected in the shell
- **Bootstrap workspace selection** — deterministic via `resolveBootstrapWorkspaceId()`
  after sequential workspace + run load (no parallel race)
- **Chat rehydration** — scoped per workspace; messages posted under one ID do not appear
  when another workspace is selected; only the latest thread per workspace is returned
- **Chat orchestration** — `POST /api/chat/messages` returns operator + system + agent
  messages; new dispatches run bounded executor (`health` / `list files` / `read …`) then
  `review_ready` with `command_execution` receipt
- **Workspace catalog** — sidebar uses seven mockup IDs; API may expose more — see
  `docs/WORKSPACE_CATALOG.md`
- Operator mode renders the right dock as **Run → Approvals → Signals → Conversation →
  Command → KAIRO Briefing** with the briefing card anchored at the bottom of the dock
- briefing data is projected across the dock rather than shown as one raw DTO
  dump: approvals stay in the approvals seam, top signals stay in the signals
  seam, and the KAIRO card stays summary/CTA-oriented
- Monaco host loads workspace files on disk and read-only DTO overview tabs
- xterm host attaches to a backend PTY scoped to the selected workspace directory
- inbox ranking uses severity, recency, unresolved duration (`created_at`), status,
  action-type, and a thin watch-owned workspace priority map

That is okay for this stage.

## Locked Shell Layout

**Locked 2026-07-04** — see `docs/UI_LAYOUT_LOCK.md` and
`docs/adr/ADR-004-locked-console-shell-layout.md`.

Do not rearrange shell regions or dock seam order without a superseding ADR.
Frozen planning in `axon-local/Plans/Axon-Watch/UI_COMPOSITION_SPEC.md` is amended
to match this geometry.

Five-region grid:

| Region | Component | Notes |
|---|---|---|
| Top bar | `TopBar.vue` | identity zone + runtime strip + KAIRO module + mode toggle |
| Left sidebar | `LeftSidebar.vue` | workspaces, optional explorer (IDE), status card |
| Center workbench | `CenterWorkbench.vue` | Monaco editor + embedded resizable terminal dock |
| Right dock | `RightDock.vue` | Run → Approvals → Signals (upper stack), KAIRO Briefing bottom hero |
| Status bar | `StatusBar.vue` | HUD runtime strip |

KAIRO Briefing height tracks the workbench terminal dock via `--briefing-dock-height`.

## Current Shell Layout

The locked shell matches the mockup/live screenshots:

- `TopBar` — brand frame, mockup breadcrumb/version context panel, DTO runtime
  strip, KAIRO presence module, Operator/IDE toggle, settings action
- `LeftSidebar` — workspace list first, workspace status card second, explorer
  tree only in IDE mode
- `CenterWorkbench` — editor tabbar + breadcrumb + Monaco editor above a
  resizable bottom terminal/log dock
- `RightDock` — run seam, approvals seam, signals seam, KAIRO briefing card
- `StatusBar` — persistent watch / run phase / signals / operator strip

This is the layout you should compare against the mockup and live screenshots,
not the older single-file shell description from earlier thin slices.

## Mockup / Live Parity Notes

Parity observations from the current mockup and live screenshots:

- the region geometry now largely matches the mockup: topbar, workspace rail,
  editor-over-terminal workbench, right dock, and bottom status strip
- the **runtime strip**, status bar zones, and workspace status card derive from
  live shell state / `RuntimeSummary`, but the topbar breadcrumb and runtime
  version chips are still mockup-style presentation helpers
- the sidebar and shell store share the same operator workspace catalog (`MOCKUP_WORKSPACE_IDS`)
- the dock uses operator-facing seam titles (`Active Run`, `Approvals`, `Signals`, `Conversation`) from `dock-seam-layout.ts`
- live shell refresh uses `GET /api/live/events` (SSE refresh hints) via `live-events-session.ts`, with visibility-aware polling fallback when EventSource is unavailable
- Operator mode renders the right dock as **Run → Approvals → Signals → Conversation →
  Command → KAIRO Briefing** with the briefing card anchored at the bottom of the dock
- the workbench terminal dock default height is ~240px (responsive cap 280px) unless the
  operator resizes it; height persists in session storage when customized

## The Most Important Files Right Now

If you need to understand the current implementation quickly, read these first:

### Shared contracts

- `packages/shared-types/src/index.ts`
- `packages/shared-types/src/run.ts`
- `packages/shared-types/src/runtime.ts`
- `packages/shared-types/src/signals.ts`
- `packages/shared-types/src/control-plane.ts`
- `packages/shared-types/src/watch.ts`

### Fixture payloads

- `packages/shared-types/fixtures/runtime-summary.example.json`
- `packages/shared-types/fixtures/watch-summary.example.json`
- `packages/shared-types/fixtures/run-record.example.json`
- `packages/shared-types/fixtures/signal-event.example.json`

### Control plane

- `services/control-plane/app/main.py`
- `services/control-plane/app/workspace_catalog.py`
- `services/control-plane/app/runs/service.py`
- `services/control-plane/app/runtime_summary_assembler.py`
- `services/control-plane/app/operator_briefing.py`

### Frontend shell

- `apps/console-web/src/main.ts`
- `apps/console-web/src/api/control-plane.ts`
- `apps/console-web/src/stores/shell.ts`
- `apps/console-web/src/App.vue`
- `apps/console-web/src/components/EditorHost.vue`
- `apps/console-web/src/components/TerminalHost.vue`
- `apps/console-web/src/lib/workspace-documents.ts`

### Verification

- `scripts/verify/README.md`
- `scripts/verify/verification_config.json`
- `tests/test_shared_contract_fixtures.py`
- `tests/test_control_plane_runtime_summary.py`
- `tests/test_verify_harness.py`

## Verification Commands

Use these from the repo root:

## Shared contract verification

```bash
npm run verify:shared-types
```

This confirms the shared-types package typechecks.

## Contract verification

```bash
npm run verify:contracts
```

This verifies:

- shared contract package typing
- shared fixture tests
- control-plane run/inbox/runtime-summary/briefing behavior
- watch signal contract alignment

## Full current verification bundle

```bash
npm run verify
```

This runs:

- contract verification
- console-web typecheck, unit test, and production build
- verify harness checks
- DTO size checks using representative fixtures

## TEST-0 acceptance (`workspace_smoke`)

Requires the dev stack (`./scripts/dev/up.sh`).

```bash
npm run verify:test0
```

This runs, in order:

1. `./scripts/dev/check-health.sh`
2. Mission control unit tests (`operator-status-radar-view`, `workbench-terminal-split`)
3. Live acceptance — `tests/test_test0_workspace_smoke_acceptance.py` against
   `workspace_smoke` (briefing Notice/Advise, git status, resume from review, inbox/runs)
4. `npm run verify`

See also `docs/OPERATOR_MISSION_CONTROL_V1.md` for the manual UI checklist.

## Latency evidence (D1)

When the dev stack is running, collect warm-route timing samples and re-run verify
with evidence files:

```bash
./scripts/dev/up.sh
npm run verify:evidence
npm run verify:nightly
```

This writes JSON under `.local/verify/` and passes them to `scripts/verify/all.py`.

Shell boot measurement:

- `scripts/dev/measure_shell_boot.py` records `shell_ready_ms`
- `auto` mode uses Playwright Chromium when installed; otherwise it measures the
  bootstrap critical path (index fetch + parallel `/api/runtime/summary`,
  `/api/inbox`, `/api/briefing`, `/api/workspaces`, `/api/runs`)
- optional full browser mode: `pip install playwright && playwright install chromium`
  then `AXON_WATCH_SHELL_BOOT_MODE=browser npm run verify:evidence`
- repo-local setup:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
```

`collect-verify-evidence.sh` prefers `.venv/bin/python3` when present so `auto` mode can use Playwright.

Example fixture: `scripts/verify/fixtures/shell-boot-report.dev.json`.

`./scripts/dev/check-health.sh` also probes `GET /api/live/events` (SSE).

## Frontend checks

```bash
npm run typecheck -w @axon-watch/console-web
npm run test -w @axon-watch/console-web
npm run build -w @axon-watch/console-web
```

## Python syntax checks

```bash
python3 -m py_compile services/control-plane/app/main.py services/control-plane/app/runs/service.py services/control-plane/app/domain/run_state.py services/control-plane/app/domain/run_transitions.py services/control-plane/app/operator_briefing.py
```

## Service tests

```bash
python3 -m unittest discover -s tests
```

## What PASS / PENDING / FAIL Mean In Verification

The verify harness uses explicit states.

### `PASS`

The supplied evidence met the rule.

Examples:

- DTO payload fits its size budget
- dependency direction rule is respected

### `PENDING`

The check exists, but the slice does not provide enough real implementation or
evidence yet.

Examples:

- shell boot timing evidence not supplied yet
- runtime summary latency budget not yet measured
- no numbered ADR yet exists

`PENDING` is not automatically bad at this stage.

It means the governance has been created ahead of the full implementation.

### `FAIL`

The rule was violated or the harness itself is broken.

This is the one that should stop you.

## Common Working Patterns

## When adding frontend work

Use real shared types from `packages/shared-types/`.

Do not:

- invent local copies of DTOs
- widen semantics casually in component code
- hide backend meaning in placeholder strings

Good pattern:

- define or refine contract in shared-types
- use it in store/API layer
- render it in Vue components

## When adding control-plane work

Prefer:

- canonical DTO assembly
- light endpoint handlers
- explicit payload validation

Avoid:

- stuffing frontend-specific assumptions into the backend
- returning huge boot payloads
- redefining contract shapes inline

## When adding watch work

Prefer:

- narrow, owned summaries
- canonical signal/event identities
- explicit watch responsibilities

Avoid:

- pulling UI logic into the watch service
- importing control-plane domain semantics directly
- inventing competing signal vocabulary

## Troubleshooting

## Debugging playbook

Use this order when something breaks:

1. **Stack health** — `./scripts/dev/check-health.sh` (all three services + key APIs).
2. **Restart clean** — `./scripts/dev/down.sh && ./scripts/dev/up.sh` after backend route changes.
3. **Browser cache** — hard refresh `:4173` (`Ctrl+Shift+R`) after console-web bundle changes.
4. **Connectors truth** — Mission Control → **Connectors** rail or `GET /api/connectors`.
5. **Gate scripts** — `npm run verify:production-operator`, then the slice gate (`verify:testN` / `verify:shell-commands`).
6. **Logs** — `.local/logs/` per service; pid files under `.local/run/`.

Symptom-specific fixes continue in the sections below.

## Problem: online research falls back / Google search returns 403

See **[docs/how-to/searxng-research.md](how-to/searxng-research.md)** for SearXNG
setup, provider order (SearXNG → legacy Google → DuckDuckGo), and Google 403
troubleshooting.

## Problem: `./scripts/dev/up.sh` fails or the frontend does not start

Check:

1. Did you run `npm install` at repo root?
2. Are ports `4173`, `8787`, and `8788` free?
3. Did `up.sh` print a specific port conflict or readiness failure message?

Current expected path:

- root install: `npm install`
- root startup: `./scripts/dev/up.sh`
- health check: `./scripts/dev/check-health.sh`

If startup fails, inspect:

- `.local/logs/console-web.log`
- `.local/logs/control-plane.log`
- `.local/logs/axon-watch.log`

## Problem: `check-health.sh` fails

This usually means one or more services never started.

Steps:

1. stop everything:

```bash
./scripts/dev/down.sh
```

2. start again:

```bash
./scripts/dev/up.sh
```

3. inspect logs:

- `.local/logs/control-plane.log`
- `.local/logs/axon-watch.log`
- `.local/logs/console-web.log`

4. re-run:

```bash
./scripts/dev/check-health.sh
```

## Problem: stale pid files block startup

`up.sh` now clears stale pid files automatically before it checks for a live stack.

First try:

```bash
./scripts/dev/down.sh
```

If that is not enough, inspect:

- `.local/pids/`
- `.local/logs/console-web.log`
- `.local/logs/control-plane.log`
- `.local/logs/axon-watch.log`

If `up.sh` still fails, it usually means one of the configured ports is held by
another live process. Free the port or stop the other process before retrying.

## Problem: the shell loads but runtime summary is unavailable

Check:

1. Is control-plane running?
2. Does this endpoint work?

```bash
curl -fsS http://127.0.0.1:8787/api/runtime/summary | python3 -m json.tool
```

3. If running through Vite dev server, is `/api` proxied to control-plane?

Current dev proxy lives in:

- `apps/console-web/vite.config.ts`

You can also override the target with:

- `VITE_CONTROL_PLANE_BASE_URL`

## Problem: `npm run verify` shows `PENDING`

That is often expected at this stage.

Examples of currently expected pending checks:

- shell boot readiness
- runtime summary latency
- watch summary latency
- numbered ADR presence

Treat `PENDING` as:

- “scaffold exists, evidence not landed yet”

Treat `FAIL` as:

- “something is wrong right now”

## Problem: dependency direction checks fail

Check for forbidden imports across boundaries.

The current verify harness guards things like:

- watch service must not depend on UI internals
- frontend must not depend on watch internals
- future domain-layer cross-imports must stay clean

If a dependency check fails:

1. remove the cross-boundary import
2. move shared meaning into `packages/shared-types/` if appropriate
3. use an adapter or API boundary instead of direct reach-through

## Problem: contract tests fail after changing fixtures or DTOs

This usually means one of three things:

1. you changed a canonical field name
2. you widened/narrowed a type without updating the fixture
3. you changed semantics without updating the contract layer first

Fix sequence:

1. check the frozen planning doc
2. check the shared contract type
3. check the fixture
4. check the consumer/provider test

Do not patch the frontend alone and ignore the canonical contract.

## Problem: you are unsure whether something should become a new ADR

Ask:

1. Is this a real architecture or process decision?
2. Is it broader than one small implementation detail?
3. Would future readers need to know why this choice was made?

If yes, use ADR governance.

Current ADR process docs live in:

- `docs/adr/README.md`
- `docs/adr/_TEMPLATE.md`

Note:

- accepted ADRs should be numbered
- accepted ADRs should not be rewritten materially
- changed decisions should be superseded, not silently edited

## Tips And Tricks

## Upgrading and updating

After pulling new commits or changing dependencies:

```bash
cd /home/edp/axon-nvme/repos/axon-watch
git pull
npm install
./scripts/dev/down.sh && ./scripts/dev/up.sh
npm run verify:production-operator
```

Sync planning docs back to axon-local when Axon-Watch planning changed:

```bash
python3 scripts/ops/sync_planning_mirror_to_axon_local.py
```

Hard-refresh `:4173` after frontend changes. Restart the stack after control-plane or watch route changes.

## Tip 1: Read the planning bundle before expanding semantics

The planning bundle is not optional context. It is the definition of intended
meaning.

## Tip 2: Treat `packages/shared-types/` as sacred

If the frontend and backend disagree, fix it here first.

## Tip 3: Keep slices narrow

The repo is intentionally growing by thin slices.

If you are touching:

- run-state
- runtime summary
- signals
- approvals

then keep the slice tightly bounded and verifiable.

## Tip 4: Prefer fixtures early

Fixtures are useful in early slices because they:

- keep contracts concrete
- make DTO size checks easy
- let frontend and backend agree before deeper logic exists

## Tip 5: Use the verify harness even when it is not strict

`PENDING` today becomes `PASS` or `FAIL` tomorrow.

The harness is part of how this repo avoids drifting back into a monolith.

## Tip 6: Distinguish “bootstrap-real” from “feature-real”

Something can be real enough to run and still be intentionally shallow.

Current examples:

- runtime summary endpoint is real
- runtime summary assembly is still bootstrap-thin
- axon-watch emits `signal_runtime_summary_degraded` with bootstrap-aware copy
  (`Bootstrap: runtime summary stale`) while watch connectivity is healthy — this
  is expected local scaffolding, not a production outage

That distinction matters during review.

## Tip 7: Do not overreact to incomplete polish

At this stage, review should focus on:

- boundaries
- ownership
- contracts
- verification

Not whether the shell is already pretty or feature-rich.

## What A Good Next Slice Looks Like

A good next slice should:

- keep shared contract semantics stable
- improve one owned behavior
- preserve boot simplicity
- come with verification

**Completed thin slices (do not re-do):**

- bootstrap + shared contracts + runtime summary
- first watch signal path
- npm workspace dev ergonomics
- first run lifecycle (create → executing → complete)
- startup supervision reliability (`scripts/dev/lib/common.sh`)
- stop/resume, approval, review-ready, SQLite persistence, and briefing-backed
  dock projections
- workspace list + backend PTY terminal + file-backed Monaco host + nested
  explorer tree + new-file creation + active-file rename + resizable bottom terminal dock
- richer inbox ranking (severity, recency, unresolved duration, status,
  action-type, workspace priority)
- split shell regions (`TopBar`, `LeftSidebar`, `CenterWorkbench`, `RightDock`,
  `StatusBar`) with mockup-shell HUD chrome
- Conversation and Command dock seams backed by control-plane chat endpoints
  (`POST /api/chat/messages`, `GET /api/workspaces/{workspace_id}/chat/thread`,
  `GET /api/chat/threads/{thread_id}/history`)

**Suggested next slices (2026-07-04):**

1. **Coordinator** — KAIRO operator-presence integration when explicitly assigned
2. **Lane B** — agent orchestration hook for chat messages (beyond system ack stub)

Bad next slices:

- broad UI rewrite
- expanding multiple semantic families at once
- changing run-state and signal-state in one uncontrolled pass
- skipping verification because “it is still early”
- claiming full IDE parity when workspace file operations are still intentionally
  thin-slice (open, edit, save, create, rename) rather than a full VS Code clone

## Final Guidance

If you are unsure what to do next, choose the smaller move that:

- preserves ownership
- strengthens verification
- reduces placeholders
- keeps the shell boot-safe

That is the design center of this repo right now.
