# AXON-X Platform Intelligence — Architectural Audit

| Field | Value |
| --- | --- |
| **Repo path** | `/home/edp/axon-nvme/repos/axon-watch` |
| **Product name** | Axon-X (folder name remains `axon-watch`) |
| **Audit date** | 2026-08-01 |
| **Method** | Read-only inspection of code, config, and in-repo docs |
| **Stance** | Describe what exists. Gaps labeled **UNKNOWN** or **DOCUMENTED INTENT**. No speculative runtime behavior. |

**Related canonical docs (prefer these for ownership/layout):**

- `ARCHITECTURE.md` — three-service boundary
- `PRODUCT.md` — thesis / non-goals
- `README.md` — bootstrap ports and verify entrypoints
- `docs/UI_LAYOUT_LOCK.md` + `docs/adr/ADR-004-locked-console-shell-layout.md` — shell geometry
- `docs/BRANCHING.md` — documented branch/remote workflow
- `docs/how-to/company-hierarchy-and-lead-checkin.md` — org / Lead check-in model

---

## Critical corrections vs an earlier draft of this audit

| Earlier claim | Correction |
| --- | --- |
| Bound workspaces ≈ 6 companies | **False.** `workspace-agents.json` has **6 companies**. `workspace-project-bindings.json` has **17 bindings**. Eleven bound roots have **no** company roster in `workspace-agents.json`. |
| Watch SQLite path UNKNOWN | **Resolved.** Default `./.local/state/axon-watch.sqlite3` (`services/axon-watch/app/persistence/watch_store_sqlite.py`). |
| Delivery applies to all companies | **False.** `workspace-delivery.json` lists only `workspace_axon_watch` and `workspace_dashpro`. |
| Live git always on `dev`/`master` | **Environment-specific.** `docs/BRANCHING.md` documents `dev`/`master` + `origin` → `axon-control-ops/axon-watch`. This working tree may be on another branch; `origin` and `fork` remotes can both exist. |
| Soft-route busy gate “exists” | **Verified** in `apps/console-web/src/lib/specialty-route-busy-gate.ts` + `use-composer-actions.ts` (skip soft specialty route when destination is live-busy; named-assign still routes). |
| “Clear failure API” absent | **Still no dedicated clear API found** under control-plane routes; roster strip follows latest role-tagged terminal outcome (`run_outcome.py`). |

---

## 1. Platform overview

### What Axon-X is

A **local-first operator + multi-company coding control stack**:

1. Vue console (Mission Control + IDE)
2. FastAPI **control plane** (run truth, chat/agents, approvals, delivery)
3. FastAPI **watch** service (signals, monitors, delivery receipts)

Canonical boundary (`ARCHITECTURE.md`):

```text
Watch detects and persists.
Control plane decides and acts.
UI presents and steers.
```

### Primary surfaces

| Path | Role |
| --- | --- |
| `apps/console-web/` | Vue 3 shell: Mission Control, IDE (Monaco/xterm), agent dock, roster, Attention |
| `apps/console-desktop/` | Tauri desktop packaging (`src-tauri/`); internals **not deeply audited** here |
| `services/control-plane/` | Runs, chat/Lane B, workspace agents, KAIRO, CLI runtime, delivery |
| `services/axon-watch/` | Inbox signals, connectors, monitoring loops, watch SQLite |
| `packages/` | Shared contracts (`packages/shared-types/`) |
| `config/` | Agents, bindings, delivery, connectors, contracts |
| `docs/` | ADRs, parity, how-tos, planning (mix of live contracts and dated status) |
| `scripts/` | `dev/up.sh`, verify gates, ops helpers |
| `infra/` | Docker / Caddy / systemd skeletons |
| `tests/` | Python contract/unit tests (verify runner isolates dual `app` packages) |

### Documented local ports (`.env.example` / README)

| Service | Default |
| --- | --- |
| Console web | `4173` |
| Control plane | `8787` |
| Watch | `8788` |

**Note:** Operators sometimes run Vite on `5173` for console HMR (`chore/add-run-5173` and local edit windows). That is an alternate frontend bind, not the documented bootstrap default.

### Persistence (verified defaults)

| Store | Default path |
| --- | --- |
| Control plane | `./.local/state/control-plane.sqlite3` (`run_store_sqlite.py`; `AXON_WATCH_STATE_DIR` can relocate) |
| Watch | `./.local/state/axon-watch.sqlite3` (`watch_store_sqlite.py`) |

---

## 2. Agent inventory

### Config source

`config/workspace-agents.json` (`schema_version: 2`).

**Default staffing template:** lead (`on_demand`), watcher (`always_on`), frontend / backend / integrations (`continuous`).

### Companies with full 5-employee rosters (6)

| Workspace ID | Company | Lead | Watcher | Frontend | Backend | Integrations |
| --- | --- | --- | --- | --- | --- | --- |
| `workspace_axon_watch` | Axon-X | Mira | Rowan | Jules | Reed | Quinn |
| `workspace_dashpro` | DashPro | Dana | Cass | Priya | Marco | Soren |
| `workspace_edudashpro_school` | EDP Excellence | Lindi | Thabo | Naledi | Sipho | Amara |
| `workspace_tps` | TPS | Noor | Blair | Vera | Hugo | Tess |
| `workspace_young_eagles_day_care` | Young Eagles | Imani | Ash | Lila | Cole | Sol |
| `workspace_axon_local` | Axon Local | Avery | Remy | Sable | Mina | Drew |

Each employee record includes: `name`, `role`, `owns`, `schedule`, optional `primary`, `azure_voice_id`. Runtime roster fields (`status`, `last_outcome`, `active_run_id`, …) are attached by `build_company_roster` in `services/control-plane/app/workspace_agents/__init__.py`.

### Project bindings vs companies

`config/workspace-project-bindings.json` maps **17** workspace IDs → `project_root` paths.

- All **6** company workspaces have bindings.
- **11** additional bindings have **no** entry in `workspace-agents.json` companies (examples: `workspace_audio_transcribe`, `workspace_edusitepro`, `workspace_bkk_invoice_system`, …).

Those extra bindings are project roots the control plane can open; they are **not** automatically 5-person companies unless later staffed in config.

### Distinct agent kinds (do not collapse)

| Kind | Meaning | Primary locations |
| --- | --- | --- |
| Company employees | Named roster roles; IDE threads + leased continuous work | `workspace-agents.json`, `workspace_agents/*` |
| Lane B runtime | Chat/agent execution via CLI backends (esp. Cursor) | `chat/lane_b_*`, `cli_runtime/*` |
| Continuous workers | Scheduler-leased role runs | `scheduler.py`, `worker_dispatch.py` |
| KAIRO / VAXON | Operator presence / briefing / voice / fleet routing — not a specialist employee | `kairo_*.py`, KAIRO planning docs |
| Verifier identity | Gate 6 acceptance actor | `verifier_*.py`, child `project.axon.yaml` |

---

## 3. Agent lifecycle

### Schedules

- `on_demand` — typical for Lead; Leads are in `SKIP_ROLES` for continuous auto-start (`lead`, `overview_agent`).
- `always_on` / `continuous` — eligible for worker scheduler (`CONTINUOUS_SCHEDULES`).

### Continuous scheduler (`workspace_agents/scheduler.py`)

| Constant / control | Value / meaning |
| --- | --- |
| Default tick | 45s (`AXON_WATCH_WORKER_SCHEDULER_INTERVAL_SECONDS`) |
| Env hard brake | `AXON_WATCH_WORKER_SCHEDULER` |
| Dispatch brake | `AXON_WATCH_WORKER_SCHEDULER_DISPATCH` |
| UI overlay | SQLite worker scheduler settings |
| Max starts per tick | 1 (`DEFAULT_MAX_STARTS_PER_TICK`) |
| Max active executing | 2 (`DEFAULT_MAX_ACTIVE_EXECUTING`) — comments cite memory / OOM |

Also participates in lead fan-out queue dispatch and autonomy work sources (e.g. Lead team check-in — see hierarchy how-to).

### Run lifecycle (`domain/run_state.py`, `runs/service.py`)

**Phases:**  
`queued` → `starting` → (`planning` \| `awaiting_approval`) → `executing` → waiting/paused/`review_ready` as applicable → `completed` \| `failed` \| `cancelled`

Capability flags from phase: `can_stop`, `can_resume`, `can_approve`, `can_review`.

### Roster outcomes / failure strips

Latest role-tagged terminal run drives `last_outcome` / `last_outcome_detail` (`run_outcome.py`). Console failure strips consume that. **No dedicated “clear employee failure” API was found**; a newer completed/failed run supersedes.

---

## 4. Context flow

### Interactive IDE employee turn (summary)

```text
Agent Dock (console-web shell)
  → optional Plan soft-switch / specialty route (client)
  → POST chat (control-plane)
  → thread + optional linked run (composer_mode)
  → Lane B system content (persona + mode + CRC)
  → CLI runtime (cursor_agent / others) + execution_access
  → stream → IDE thread / stream UI map
  → finalize (Confidence, Gate 6 if task-bound, complete/fail)
```

### Continuous worker turn (summary)

```text
Scheduler tick → lease task for role → create_run(employee_role)
  → worker_dispatch → continuous worker prompt → Lane B
  → optional isolation + IDE stream mirror → receipts → complete/fail
```

### Org communication model

Documented in `docs/how-to/company-hierarchy-and-lead-checkin.md`:

```text
Operator ↔ VAXON ↔ Company Lead ↔ Specialists
```

Cross-company ownership guidance is also injected into Lead persona prompts (`fleet_leads_context.py` / handoff language in `employee_persona_prompt.py`).

**UNKNOWN:** Exhaustive per-mode branch table for every Lane B fast path (`lane_b_*_fast_path.py`) was not fully expanded in this audit.

---

## 5. Prompt architecture

| Layer | Module | Role |
| --- | --- | --- |
| Standing accuracy + Critical Review Clause | `critical_review_clause.py` | Shared accuracy contract; finalize expects `Confidence: N/10` |
| Employee persona | `employee_persona_prompt.py` | Identity, owns, roster, fleet leads (Lead), first-person rules |
| Continuous worker | `worker_prompt.py` | Task/goal scope, CI clauses, memory safety, CRC |
| Team / fleet | `team_roster_context.py`, `fleet_leads_context.py` | In-company roster; cross-company Lead map |
| Specialty bags | `teammate_route_bags.py` + TS `composer-teammate-route.ts` | Keyword scoring (dual implementation — drift risk) |
| Plan CLI | `cli_runtime/plan_system_prompt.py` | Plan-mode system prompt |
| KAIRO | `kairo_*.py` | Operator conversation — separate from employee CRC completion |

Composer modes in UI: **ask**, **plan**, **agent**, **debug**, **kairo**.  
Tool-capable (`composer-tool-modes.ts` / approval gate): **agent**, **debug**.  
Run-linked: **agent**, **debug**, **plan**.

---

## 6. Tool permissions

From `cli_runtime/approval_gate.py`:

- `execution_access`: `consultative` \| `full`
- Dock **Full Access** consent bypasses per-run approval and enables tool-capable CLI when mode allows
- Env `AXON_WATCH_AGENT_TOOL_EXECUTION` enables legacy tool path (may still require approval)
- Tool tier requires run phase `executing` for tool-capable modes; blocked in approval/paused/terminal/etc.

`.env.example` still sets `AXON_WATCH_TOOL_CALLING_SUPPORTED=false` and `AXON_WATCH_REASONING_SUPPORTED=false` — fabric flags; Cursor CLI tools still apply on the Full Access path when that path is used.

**Sandbox:** Console has sandbox composer chrome. **Enforcement depth beyond UI flags: UNKNOWN** in this audit.

**Gate 6 path policy:** Child repos declare `project.axon.yaml` allowed paths; control plane requires acceptance evidence for **task-bound** workers before `review_ready` / complete from executing (`verifier_contract.py`).

---

## 7. Memory model

| Store | Evidenced contents |
| --- | --- |
| Control-plane SQLite | Runs, transitions/receipts, tasks, chat threads/messages/attachments, scheduler settings, delivery refs, operator memory columns, host context, research cache, safe-improvement |
| Watch SQLite | Events, delivery receipts, commands, related watch persistence (`watch_store_sqlite.py` and consumers) |
| Browser storage | Layout / dock / sidebar / composer prefs (console-web) |
| Session stream UI map | Thread-keyed stream chrome in shell store — session-scoped, not durable run history |
| KAIRO participant memory | Modules present (`kairo_participant_memory.py`); full retention semantics **not fully audited** |

---

## 8. Planning pipeline

| Mechanism | Location | Behavior |
| --- | --- | --- |
| Composer Plan mode | console + Lane B plan | Soft-switch offer/switch (`composer-plan-auto-switch.ts`) |
| Lead task plan / fan-out | `lead_task_plan.py`, `lead_fan_out.py`, chat fast paths | Decompose → specialist tasks/runs |
| Lead team check-in | `lead_team_checkin.py` + autonomy work sources | Periodic assign / escalate |
| Specialty soft-route | TS + Python | Route to owning role; busy destination skipped on soft route (console) |
| Named assign | `named_assign_route` | Explicit assign/have &lt;Name&gt; |
| Cross-workspace handoff | handoff APIs + Lead prompts | Prefer handoff over foreign-repo work |

`ARCHITECTURE.md` states pure ReAct should not be the backbone; implementation mixes structured runs/tasks, Lead fan-out, and prompt CRC — **not** a Temporal-style durable workflow engine today.

---

## 9. Execution pipeline

1. **Interactive:** chat POST → Lane B (`lane_b_agent`, `lane_b_stream_execute`) → `cli_runtime` (notably `cursor_agent.py`; also claude/codex modules).
2. **Continuous:** scheduler → `dispatch_continuous_worker_run` → Lane B + optional IDE stream mirror.
3. **Operator start / board:** `operator_start_task.py` and related Lead board pickup.
4. **Isolation:** `worker_isolation.py` for continuous workers when used.
5. **Long-running shell helpers:** `long_running_shell.py` (+ prompt guidance).

Streaming: chat stream hub + worker IDE stream; architecture doc prefers SSE for one-way UI updates.

---

## 10. Verification pipeline

### Two different “gate” vocabularies

**A. Autonomy / worker gates**

| Gate | Meaning |
| --- | --- |
| Gate 6 | `acceptance_evidence` required for task-bound workers before `review_ready` / complete (`verifier_contract.py`) |
| Gate 9 | CI remediation (`ci_remediation/`, `docs/how-to/ci-remediation-gate9.md`) |
| CRC | Final `Confidence: N/10` or fail with missing-confidence detail |

**B. Axon-X repo verify / Phase G**

`docs/PHASE_G5_GATE_DESIGN.md` and `scripts/verify/*` — contracts, console-web, vault, connector parity, Phase A/B/D bundles. **Different numbering** from Gate 6/9.

### Delivery / CI watch config

`config/workspace-delivery.json`:

- Defaults: `push_policy: draft_pr`, protected branches include `main`/`master`/`dev`/`production`/`release`
- Configured workspaces: **`workspace_axon_watch`** (base `dev`, workflow “Axon-X Fast Gate”), **`workspace_dashpro`** (base `development`, multiple workflow names)

---

## 11. Git workflow

### This repo (documented)

`docs/BRANCHING.md`: day-to-day **`dev`**, baseline **`master`**, `origin` → `https://github.com/axon-control-ops/axon-watch`.

### This working tree (environment)

May be on a feature/worker branch; remotes observed can include both `origin` and `fork`. Treat `BRANCHING.md` as the **documented** workflow, not a guarantee of the current checkout.

### Worker delivery

Draft PR into configured `base_branch`; do not treat draft-PR delivery as configured for every bound workspace — only those listed in `workspace-delivery.json`.

### Child product repos

Bound via `workspace-project-bindings.json` to external trees (e.g. DashPro). Their branch policies (e.g. `development` / `preview` / `main`) are product-owned.

---

## 12. Communication patterns

| Channel | Pattern |
| --- | --- |
| IDE employee threads | Per-employee threads; tab bar; stream chrome |
| Teammate route banners | Soft-route notice + Undo (console) |
| Attention / briefing | Operator briefing + Attention stack; IDE activity bar Attention control → `IdeAttentionPanel` |
| Watch → CP → UI | Watch produces signals; CP aggregates briefing/inbox; UI presents |
| Cross-company | Handoffs API + Lead fleet map in prompts |
| Voice | Azure voice IDs on employees; KAIRO spoken alerts |
| Live events | `live_event_hub.py` / `live_events.py` |

---

## 13. Strengths

- Clear three-service ownership documented and reflected in tree layout.
- Persisted run state machine with transitions/receipts.
- Multi-company roster with owns/schedules as first-class config.
- CRC + Gate 6 push leased workers toward evidence-based completion.
- Rich operator shell with layout lock / ADR discipline.
- Delivery + CI remediation configs for selected workspaces.
- Large automated verify surface under `scripts/verify`.

---

## 14. Weaknesses

- Dual gate numbering (Phase G vs autonomy Gate 6/9) confuses onboarding.
- Dual specialty-route bags (Python + TypeScript) can drift.
- Scheduler memory caps vs desire for many parallel agents.
- Failure UX tied to latest role outcome (synthetic completions can mask reality).
- `docs/` mixes live contracts and dated status reports.
- Env flags claim tool-calling/reasoning unsupported while Full Access Cursor path is a primary execution fabric — messaging mismatch.
- Many project bindings lack company staffing — operator may open a tree with no five-person roster.

---

## 15. Technical debt

- Console shell store size / planned splits (`docs/planning/SLICE-FS-003-shell-store-split.md` and related).
- Legacy Axon Local connector inventory still present.
- Continuous-worker OOM history encoded as hard scheduler caps.
- Child-repo CI policies (e.g. self-hosted) documented per product, not one platform CI contract.
- Repo-root terminal history / zcompdump noise files.

---

## 16. Architectural risks

1. Control plane concentrates chat, agents, KAIRO, delivery, and CLI — large restart/blast radius.
2. Cursor CLI as execution fabric couples platform reliability to host auth/usage/process limits.
3. SQLite local-first; multi-host story is “adapters later,” not proven here.
4. Prompt-as-policy (owns, handoffs, CI runner rules) can be ignored unless tools/gates enforce it.
5. Parallel route implementations (console vs CP) risk inconsistent assignment.
6. Freeform IDE runs without `task_id` can bypass Gate 6 acceptance discipline.

---

## 17. Opportunities for improvement

*(Suggestions only — not implemented by this audit.)*

- Publish a single glossary for gate vocabularies and agent kinds.
- Generate TS route bags from Python (or shared JSON fixtures).
- Add an explicit failure-acknowledge API if operators must clear strips without synthetic runs.
- Index docs as authoritative vs historical.
- Optionally enforce CI `runs-on` policy in verifier where products claim it locked.
- Clarify staffing rules for bound-but-unstaffed workspaces.

---

## Onboarding map (senior engineer, day 1)

1. Read `README.md`, `ARCHITECTURE.md`, `docs/UI_LAYOUT_LOCK.md`.
2. Boot with `./scripts/dev/up.sh`; hit `/api/health`, `/api/briefing`, `/api/workspaces/{id}/company`.
3. Trace one Agent Dock send: console shell → chat service → `lane_b_*` → `cursor_agent.py`.
4. Trace one continuous tick: `scheduler.py` → `worker_dispatch.py` → CRC / Gate 6.
5. Diff `workspace-agents.json` (companies) vs `workspace-project-bindings.json` (roots) vs `workspace-delivery.json` (delivery).
6. Read `docs/how-to/company-hierarchy-and-lead-checkin.md`.

---

## Confidence

**Confidence: 8/10**

Raised from a prior draft after verifying bindings vs companies, watch SQLite path, delivery workspace list, busy-route gate presence, scheduler constants, and remotes. Remaining uncertainty: full Lane B fast-path matrix, desktop Tauri internals, sandbox enforcement depth, and KAIRO memory retention details.
