# AXON-X Constitution Gap Audit

Date: 2026-08-09
Auditor: Codex
Source of truth: `/home/edp/.codex/attachments/126c4280-1dd3-4e2a-8c60-36dd0f01766d/pasted-text.txt`
Repo audited: `/home/edp/axon-nvme/repos/axon-watch`

## Executive summary

AXON-X already has important execution foundations: persisted runs, chat threads, worker scheduler settings, workspace tasks, Lead plans, several receipt streams, operator memories, host-context receipts, runtime health/readiness probes, VAXON/operator briefing surfaces, worker isolation helpers, and a task-board/agent UI.

The constitution, however, describes a broader Executive Operating System with first-class registries and engines for evidence, missions, decisions, knowledge, planning, learning, governance, observability, and safe autonomy. The current repo is still mostly an execution/control-plane system with partial executive layers. Many roadmap nouns exist as docs, UI projections, or narrow receipt stores, but not yet as unified persistent domain models with APIs, lifecycle rules, tests, and dashboards.

The implementation should therefore proceed in strict roadmap order:

1. Close Phase 1 platform-stabilization gaps.
2. Promote existing briefing/VAXON pieces into a real Executive Intelligence layer.
3. Add the canonical registries before adding more autonomous behavior.
4. Wire current workers, Lead plans, receipts, and memories into those registries.
5. Only then expand safe autonomy, learning, and governance.

Do not start by building “JARVIS intelligence” features. The repo is not ready for that without the registry spine.

## Evidence inspected

- Constitution attachment: `/home/edp/.codex/attachments/126c4280-1dd3-4e2a-8c60-36dd0f01766d/pasted-text.txt`
- Core SQLite schema: `services/control-plane/app/persistence/run_store_sqlite.py`
- Task ledger: `services/control-plane/app/persistence/task_store.py`
- Autonomy receipts: `services/control-plane/app/persistence/autonomous_attention_store.py`
- Lead plans/receipts: `services/control-plane/app/workspace_agents/lead_plan_store.py`
- Lead planning model seam: `services/control-plane/app/workspace_agents/lead_plan_model.py`
- Worker isolation: `services/control-plane/app/workspace_agents/worker_isolation.py`
- Worker scheduler/gates: `services/control-plane/app/workspace_agents/scheduler.py`, `services/control-plane/app/workspace_agents/scheduler_auto_start_gates.py`
- Autonomy safety policy: `services/control-plane/app/workspace_agents/autonomous_attention_policy.py`
- Operator briefing API/projection: `services/control-plane/app/routes/operator.py`, `services/control-plane/app/operator_briefing.py`
- Runtime health/readiness: `services/control-plane/app/routes/health.py`, `services/control-plane/app/runtime_summary_assembler.py`
- Delivery receipts: `services/control-plane/app/workspace_delivery/receipts.py`, `services/control-plane/app/workspace_delivery/store.py`
- Existing docs: `docs/AXON-X-AUTONOMY-MASTER-PLAN.md`, `docs/AXON-X-AUTONOMY-READINESS.md`, `docs/adr/*`
- Live local DB tables in `.local/state/control-plane.sqlite3`

## Current persistent tables found

The local control-plane DB currently has these relevant tables:

- `runs`, `run_history`
- `chat_threads`, `chat_messages`, `chat_attachments`
- `workspace_tasks`, `workspace_handoffs`
- `lead_plans`, `lead_plan_tasks`, `lead_plan_receipts`, `lead_adhoc_receipts`
- `autonomy_attention_receipts`, `autonomy_attention_meta`
- `operator_memories`, `kairo_session_memory`, `kairo_voice_log`
- `worker_scheduler_settings`, `operator_presence_settings`, `workspace_composer_prefs`
- `host_devices`, `host_snapshots`, `host_events`, `host_artifacts`, `host_action_receipts`, `host_policy`
- `workspace_deliveries`
- `safe_improvement_cases`, `safe_improvement_proposals`, `safe_improvement_traces`
- `research_cache`

Missing as first-class constitution registries:

- `evidence_registry`
- `mission_registry`
- `decision_registry`
- `knowledge_registry`
- `lesson_registry`
- `risk_registry`
- `capability_registry`
- `adr_registry`
- `architecture_registry`
- `pattern_registry`
- `technical_debt_registry`
- `operator_preference_registry`
- `governance_registry`

Some of these concepts are partially represented by existing stores, but the constitution requires durable, independently addressable registries with traceability and success criteria.

## Phase-by-phase audit

### Phase 1 — Platform Stabilization

Status: Partial.

Implemented or partly implemented:

- Mutating auth middleware exists (`services/control-plane/app/auth/middleware.py`).
- Health/readiness endpoints exist (`services/control-plane/app/routes/health.py`).
- Runtime summary aggregates watch, CLI runtime, active runs, approvals, connectors (`services/control-plane/app/runtime_summary_assembler.py`).
- Worker scheduler has bounded tick/start limits and auto-start gates.
- Worker isolation helper exists (`services/control-plane/app/workspace_agents/worker_isolation.py`).
- Run history and receipts exist.
- Many UI/unit tests exist for composer, runtime, briefing, task board, recovery, and VAXON interactions.

Gaps:

1. No single Phase 1 stabilization checklist enforced in code.
2. No route authorization matrix covering every mutating endpoint.
3. No typed configuration validation boot gate for required environment variables and unsafe combinations.
4. Health is split between liveness/readiness/runtime summary, but there is no unified platform-health registry or persisted health timeline.
5. Logging is not normalized into an evidence registry.
6. Technical debt is documented in places but not tracked as a persistent debt register.
7. Dependency audit/dead-code detection are not continuous gates.
8. Restart safety is partial: runs persist, but mission progress/checkpoints are not modeled as durable mission state.

Claude implementation target:

- Create the Phase 1 stabilization spine first: auth matrix, config validator, platform health snapshot store, technical debt register, and stabilization dashboard/API projection.

### Phase 2 — Executive Intelligence Layer

Status: Partial.

Implemented or partly implemented:

- VAXON/operator presence settings exist.
- Operator briefing endpoint exists (`/api/briefing`).
- Executive-looking UI surfaces exist (`BriefingPanel`, VAXON composer, fleet health, task board review).
- Lead and specialist roles are modeled.

Gaps:

1. VAXON is not yet a first-class Executive Intelligence engine with persisted intent, portfolio, and decisions.
2. Executive briefings are projections over current signals/runs; they are not stored as durable briefing records with evidence refs.
3. No Mission Portfolio registry exists.
4. No Decision Engine exists as a domain boundary. There are policy decisions, autonomy receipts, and host action decisions, but no canonical executive decision model.
5. No explicit “VAXON orchestrates, never executes” enforcement boundary beyond scattered prompts/policies.

Claude implementation target:

- Add an Executive Intelligence domain that references existing run/task/receipt systems instead of duplicating execution.
- Persist executive briefings and executive intent with evidence refs.
- Add tests proving executive outputs reference execution evidence and do not claim execution.

### Phase 3 — Knowledge Layer

Status: Mostly missing.

Implemented or partly implemented:

- `operator_memories` can store notes/research/reminders.
- `kairo_session_memory` stores conversational/session state.
- Research capture can write memories.

Gaps:

1. No Evidence Registry.
2. No Knowledge Registry.
3. No Decision Registry.
4. No Pattern Registry.
5. No Lesson Registry.
6. No Architecture Registry.
7. Existing memory is useful but too generic to satisfy organizational knowledge requirements.
8. Receipts remain scattered across run history, Lead plan receipts, autonomy receipts, delivery receipts, host receipts, and safe-improvement traces.

Claude implementation target:

- Build a canonical registry schema and service layer that can index existing receipts without moving/destructively rewriting them.
- Add `source_ref`/`evidence_ref` abstractions that point to existing run history, Lead receipts, autonomy receipts, delivery receipts, host receipts, and docs.

### Phase 4 — Planning Layer

Status: Partial.

Implemented or partly implemented:

- Durable Lead plans exist (`lead_plans`, `lead_plan_tasks`, `lead_plan_receipts`).
- Workspace task ledger exists.
- Lead planning model seam exists for decomposing specialist work.
- Dependencies exist on `workspace_tasks.dependencies_json`.

Gaps:

1. No Mission Specification Engine.
2. No Mission Dependency Graph as a first-class model.
3. No Mission Timeline.
4. No Mission Risk Analysis beyond simple task `risk`.
5. No Resource Allocation engine.
6. Lead plans are workspace/task oriented, not executive mission oriented.

Claude implementation target:

- Add mission model tables/services and link Lead plans/tasks to missions.
- Preserve Lead plan behavior; do not replace it.
- Provide migration/indexer that can create mission records from existing active Lead plans.

### Phase 5 — Decision Layer

Status: Partial, fragmented.

Implemented or partly implemented:

- Autonomy attention receipts include decision/tier/risk/status.
- Host context action evaluation returns decisions and receipts.
- Autonomy safety policy classifies safe vs operator-gated work.

Gaps:

1. No canonical Decision Register.
2. No decision history spanning VAXON, Lead, task scheduler, host actions, and operator approvals.
3. No standard confidence/explainability fields across all decisions.
4. No trade-off/alternative evaluation model.
5. No decision-to-evidence trace contract.

Claude implementation target:

- Introduce a canonical decision record and adapters from current decision sources.
- Add tests that every autonomous dispatch decision has: actor, reason, tier, risk, evidence refs, confidence or explicit `confidence_unavailable`.

### Phase 6 — Learning Layer

Status: Missing.

Implemented or partly implemented:

- Some reports/docs contain lessons manually.
- Scheduler gates react to recent failures such as usage limits, billing, runtime auth, and generic backoff.

Gaps:

1. No Outcome Evaluation engine.
2. No Recommendation Learning.
3. No Engineering/Organizational/Strategic learning model.
4. No pattern extraction pipeline from receipts and failures.
5. No success/failure pattern registries.

Claude implementation target:

- After registries exist, add a lightweight learning indexer that summarizes terminal runs/tasks into lesson/pattern candidates requiring review before becoming standards.

### Phase 7 — Autonomy Layer

Status: Partial.

Implemented or partly implemented:

- Worker scheduler exists.
- Auto/full mode toggles scheduler enabled state.
- Task leasing and attempts exist.
- Worker isolation helper exists.
- Auto-start gates exist for usage/billing/auth/generic failures.
- VAXON auto-attend UI/API exists.

Gaps:

1. Checkpoints are not first-class.
2. Resume engine exists for runs but not mission-level recovery.
3. Autonomous scheduling is task-based, not mission/portfolio-based.
4. Autonomous recovery does not consistently self-heal capability gaps such as missing allowlists/tools.
5. Safe Delegation is partial; recent observed behavior shows routing/composer ambiguity can still occur.
6. Continuous improvement lacks a governance-backed loop.

Claude implementation target:

- Add mission checkpoints and resume contracts.
- Connect scheduler decisions to mission/task/decision/evidence records.
- Add explicit blocker classification: safe self-heal, operator-gated, or impossible-with-current-tools.

### Phase 8 — Engineering Governance

Status: Mostly documentation.

Implemented or partly implemented:

- ADR docs exist in `docs/adr`.
- Technical and planning docs exist.
- Some safety policies exist in code.

Gaps:

1. No ADR Registry.
2. No Architecture Review Engine.
3. No Technical Debt Engine.
4. No Capability Lifecycle model.
5. No Quality Gate registry.
6. No enforcement that new work outside the constitution requires an ADR.

Claude implementation target:

- Implement governance registry and a preflight check that can flag new capability files/routes without a linked capability spec/ADR.

### Phase 9 — Observability

Status: Partial.

Implemented or partly implemented:

- Runtime summary exists.
- Operator fleet health exists.
- Briefing and task board projections exist.
- Host context stores snapshots/events/artifacts/receipts.

Gaps:

1. No unified platform dashboard backed by canonical health records.
2. No mission health model.
3. Agent health exists mostly as current run/roster state, not historical health.
4. Dependency health is mostly runtime/inbox-derived, not persisted.
5. Executive metrics are not first-class.

Claude implementation target:

- Persist platform/agent/mission/dependency health snapshots and expose read APIs.
- Keep dashboard additions read-only first.

### Phase 10 — Developer Experience

Status: Partial.

Implemented or partly implemented:

- Docs are rich.
- API clients exist in console web.
- Prompt-related UI utilities exist.
- Skills/slash command UI has tests.

Gaps:

1. No Documentation Generator.
2. No Architecture Explorer.
3. No Capability Explorer backed by `capability_registry`.
4. No API Explorer.
5. No Prompt Explorer backed by prompt records.
6. Knowledge search is limited to operator memories/research, not full registries.

Claude implementation target:

- Defer until registries exist.
- Add only read-only explorer stubs once capability/evidence/architecture registries are implemented.

### Phase 11 — JARVIS Intelligence

Status: Not ready.

Gaps:

- Multi-project awareness is partial through workspace bindings and fleet views.
- Strategic planning/recommendations/forecasting/simulation are not safe to add before decision, evidence, mission, and governance registries exist.

Claude implementation target:

- Do not implement yet except by adding ADR/capability specs.

### Phase 12 — Future Intelligence

Status: Not ready.

Gaps:

- Memory consolidation, capability evolution, self evaluation/calibration, controlled self-improvement, cross-project learning, and executive research are not yet backed by the required registry/governance safety systems.

Claude implementation target:

- Do not implement yet except specs and governance guardrails.

## Highest-priority gaps to implement now

### P0 — Canonical registry spine

Add persistent, versioned registries without deleting or replacing existing stores:

- Evidence Registry
- Mission Registry
- Decision Registry
- Capability Registry
- ADR Registry
- Technical Debt Registry
- Platform Health Registry

Why first:

- The constitution repeatedly requires traceability, evidence, and survivable mission context.
- Current data is scattered across many receipt/history tables.
- Later intelligence/autonomy features need a canonical reference layer.

Acceptance:

- New tables are created idempotently in SQLite schema helpers or dedicated stores.
- Existing receipts can be indexed by source reference.
- Read APIs expose the registries.
- Unit tests prove records survive reconnect/restart and preserve source refs.

### P0 — Executive action evidence contract

Create one contract for any VAXON/Lead/scheduler recommendation or action:

- actor
- capability id
- mission id/task id/run id where applicable
- decision id where applicable
- evidence refs
- risk/tier
- explanation
- confidence or explicit unavailable marker
- created/updated timestamps

Why:

- Prevents invented completion.
- Lets VAXON orchestrate without duplicating execution.
- Makes autonomous behavior inspectable.

Acceptance:

- VAXON briefing actions include evidence refs.
- Scheduler dispatch receipts include decision/evidence refs.
- Lead fan-out receipts include mission/task/decision refs.
- Tests fail if a completion/action claim has no evidence refs.

### P0 — Stabilization/governance gate

Add a local preflight that checks:

- mutating routes are covered by auth policy;
- config is valid;
- no new capability route/service exists without capability registry entry;
- no new architecture-sensitive change exists without ADR/capability spec;
- autonomy-critical tests are runnable.

Acceptance:

- A script such as `scripts/dev/check-constitution-gates.sh` or equivalent exists.
- CI/local verification can run it.
- It reports actionable failures instead of vague warnings.

### P1 — Mission model over Lead/task execution

Add mission records and link them to:

- Lead plans
- workspace tasks
- runs
- receipts/evidence
- decisions
- checkpoints

Acceptance:

- Creating a Lead plan can attach to a mission.
- Mission survives service restart.
- Mission dashboard/API can show status, risks, next action, and evidence.

### P1 — Decision Register

Unify scattered decisions from:

- autonomy attention policy
- scheduler lease gates
- host action evaluator
- Lead/VAXON handoff decisions
- operator approvals

Acceptance:

- Decision records are queryable by mission/task/run.
- Every autonomous dispatch has a decision record.
- Every operator-gated action has a pending/resolved decision lifecycle.

### P1 — Knowledge/lesson/pattern indexer

After Evidence/Mission/Decision registries exist:

- summarize terminal tasks/runs into candidate lessons;
- detect recurring blocker patterns;
- require approval before promoting patterns to standards.

Acceptance:

- Failed worker runs generate failure pattern candidates.
- Successful verified deliveries generate success pattern candidates.
- No candidate is presented as approved knowledge until reviewed.

## Explicit non-goals for Claude's first implementation pass

- Do not rebuild the execution runtime.
- Do not replace Lead, Specialists, REPORT, task ledger, run history, or worker scheduler.
- Do not implement Phase 11/12 “JARVIS” strategy features yet.
- Do not auto-approve destructive or irreversible actions.
- Do not fabricate migration success; add tests and receipts.
- Do not edit the constitution attachment.

## Claude implementation handoff

Use this prompt for Claude:

```md
You are implementing the AXON-X Engineering Constitution gap closure in `/home/edp/axon-nvme/repos/axon-watch`.

Source of truth:
- `/home/edp/.codex/attachments/126c4280-1dd3-4e2a-8c60-36dd0f01766d/pasted-text.txt`

Audit to implement:
- `docs/ops/agent-reports/axon-x-constitution-gap-audit-2026-08-09.md`

Mission:
Close the highest-priority gaps between the current AXON-X repo and the constitution, in roadmap order. Start with the registry/evidence spine and stabilization/governance gates. Do not jump to JARVIS/strategic intelligence features.

Rules:
1. Extend existing subsystems; do not replace execution, Lead, Specialists, REPORT, task ledger, run history, worker scheduler, or existing receipt streams.
2. Evidence before action. Every new executive/autonomous action must reference existing execution evidence or explicitly state evidence is unavailable.
3. Add persistent SQLite-backed registries before adding more autonomy:
   - Evidence Registry
   - Mission Registry
   - Decision Registry
   - Capability Registry
   - ADR Registry
   - Technical Debt Registry
   - Platform Health Registry
4. Keep migrations idempotent and compatible with the existing `.local/state/control-plane.sqlite3` schema.
5. Add read APIs and focused tests for each new registry/service.
6. Add a constitution gate/preflight that checks auth-route coverage, config validity, capability/ADR linkage, and autonomy-critical test availability.
7. Make the first implementation pass small and shippable: schema + stores + APIs + tests + docs/handoff updates. Do not attempt all 12 phases in one giant edit.
8. End with a critical review of your own work and `Confidence: X/10`.

Suggested first slice:
- Add `services/control-plane/app/persistence/constitution_registry_store.py` or similarly named stores.
- Add idempotent schema creation for evidence, missions, decisions, capabilities, ADRs, technical debt, and platform health.
- Add minimal route(s), preferably under `/api/operator/constitution/*` or a similarly clear namespace, for read-only registry inspection and health snapshot retrieval.
- Add adapters/index helpers that can create evidence refs pointing to existing `run_history`, `lead_plan_receipts`, `autonomy_attention_receipts`, `host_action_receipts`, and `workspace_deliveries` without copying or destroying historical records.
- Add tests that use isolated SQLite DB paths and prove persistence, source refs, and decision/evidence traceability.
- Add docs showing how this maps to Phase 1–3 of the constitution.

Before editing:
- Run `git status --short --branch`.
- Inspect current schema/store patterns in `services/control-plane/app/persistence/run_store_sqlite.py`, `task_store.py`, `autonomous_attention_store.py`, and `workspace_agents/lead_plan_store.py`.
- Preserve unrelated user changes.

Verification:
- Run the focused backend tests you add.
- Run the smallest relevant existing frontend/backend tests if routes or shared API shapes change.
- If a broader test cannot run, report the exact command and failure.
```

## Recommended implementation order for Claude

1. Registry schema/store layer.
2. Read APIs for registry visibility.
3. Evidence-ref adapters for existing receipt sources.
4. Decision contract and minimal decision register integration.
5. Mission model linked to Lead plans/tasks/runs.
6. Platform health snapshot persistence.
7. Constitution gate script.
8. UI/dashboard read-only projections.
9. Learning/governance/autonomy expansion after registry tests are green.

## Implementation progress ledger

### 2026-08-09 — Codex first slice started

Status: completed first registry-spine slice; not committed yet.

Files added:

- `services/control-plane/app/persistence/constitution_registry_store.py`
- `services/control-plane/app/persistence/evidence_ref_adapters.py`
- `services/control-plane/app/routes/constitution.py`
- `tests/test_constitution_registry.py`

Files changed for this slice:

- `services/control-plane/app/routes/__init__.py` registers the new constitution router.

Important workspace note:

- Several runtime-policy files were already modified before this slice. They were preserved and not reviewed as part of this constitution work:
  - `apps/console-web/src/api/workspace-api.ts`
  - `apps/console-web/src/components/settings/WorkspaceRuntimePolicyPanel.vue`
  - `apps/console-web/src/styles/settings/workspace-runtime-policy.css`
  - `services/control-plane/app/persistence/run_store_sqlite.py`
  - `services/control-plane/app/persistence/workspace_composer_prefs_store.py`
  - `services/control-plane/app/routes/schemas.py`
  - `services/control-plane/app/routes/workspaces.py`
  - `services/control-plane/app/workspace_agents/worker_dispatch.py`

Implemented:

- Added idempotent SQLite-backed constitution registries:
  - Evidence Registry
  - Mission Registry
  - Decision Registry
  - Capability Registry
  - ADR Registry
  - Technical Debt Registry
  - Platform Health Registry
- Added evidence indexing that references existing source records instead of copying/replacing execution stores.
- Added evidence adapters for:
  - `run_history`
  - `lead_plan_receipts`
  - `autonomy_attention_receipts`
  - `host_action_receipts`
  - `workspace_deliveries`
- Corrected the previous Claude partial-work assumption: `run_history` is keyed by `(history_ref, sequence)` with `transition_json`; it does not have `run_id`, `workspace_id`, or `stopped_at` columns. The implemented adapter joins to `runs` by `history_ref`.
- Added read APIs under `/api/operator/constitution/*`.
- Added registry visibility for capabilities, ADRs, technical debt, evidence, missions, decisions, and platform health.
- Added mutating-but-auth-covered APIs for creating missions, capabilities, health snapshots, checkpoints, and evidence backfill.
- Added a decision guard: `auto_safe` and `operator_gated` decisions must include evidence IDs.

Verification:

```bash
python -m pytest tests/test_constitution_registry.py -q
# 4 passed

python -m pytest tests/test_control_plane_runs.py tests/test_control_plane_operator_briefing.py -q
# 32 passed

python -m py_compile services/control-plane/app/persistence/constitution_registry_store.py services/control-plane/app/persistence/evidence_ref_adapters.py services/control-plane/app/routes/constitution.py tests/test_constitution_registry.py
# passed
```

Next recommended slice:

1. Add a constitution gate/preflight script that checks:
   - mutating route coverage;
   - config validity;
   - capability/ADR linkage for new constitution-level routes;
   - autonomy-critical test availability.
2. Integrate registry writes into existing subsystems:
   - scheduler dispatch decisions;
   - Lead fan-out receipts;
   - VAXON handoff/briefing decisions;
   - platform health snapshots from runtime summary.
3. Add a small console read-only dashboard panel for the new constitution overview endpoint.

### 2026-08-09 — Codex constitution gate slice completed

Status: completed; not committed yet.

Files added:

- `scripts/verify/check_constitution_gates.py`
- `tests/test_constitution_gate_script.py`

Files changed:

- `package.json` adds `verify:constitution`.

Implemented:

- Added a static constitution preflight gate that checks:
  - required registry tables are declared;
  - evidence adapters respect the actual `run_history(history_ref, sequence, transition_json)` schema;
  - constitution routes are registered;
  - first-slice constitution endpoints are present;
  - FastAPI installs `MutatingAuthMiddleware`;
  - mutating routes are covered by auth middleware except intentional exemptions;
  - focused registry tests and this handoff ledger are present.
- Added a pytest guard so the gate itself is covered.

Verification:

```bash
npm run verify:constitution
# PASS constitution_registry_tables
# PASS constitution_run_history_adapter
# PASS constitution_route_registration
# PASS constitution_registry_endpoints
# PASS mutating_auth_middleware_registered
# PASS mutating_methods_guarded: 115 mutating routes covered by middleware; 2 intentional exemptions
# PASS constitution_registry_tests
# PASS constitution_handoff_ledger

python -m pytest tests/test_constitution_registry.py tests/test_constitution_gate_script.py -q
# 5 passed
```

Next recommended slice:

1. Write platform health snapshots from runtime summary into `platform_health_registry`.
2. Add decision/evidence integration for the scheduler and Lead fan-out path.
3. Add a read-only console surface for `/api/operator/constitution`.

### 2026-08-09 — Codex platform health capture slice completed

Status: completed; not committed yet.

Files added:

- `services/control-plane/app/constitution_health.py`

Files changed:

- `services/control-plane/app/routes/constitution.py`
- `scripts/verify/check_constitution_gates.py`
- `tests/test_constitution_registry.py`

Implemented:

- Added helpers to derive a constitution health status from the existing runtime summary:
  - `ready`
  - `degraded`
  - `watch_unavailable`
- Added `record_runtime_summary_health_snapshot(...)` so runtime-summary evidence can be persisted into `platform_health_registry`.
- Added auth-covered endpoint:
  - `POST /api/operator/constitution/health/capture-runtime-summary`
- Updated `verify:constitution` so the endpoint is part of the required constitution surface.
- Added tests for:
  - runtime-summary health status derivation;
  - persisted platform health snapshots;
  - the health capture endpoint.

Why this improves AXON-X:

- Runtime health is no longer only a live/ephemeral projection.
- Future autonomous dispatches can capture platform state before acting.
- Failures can be interpreted against evidence of whether Watch, runtime, or connectors were degraded at the time.
- The capture endpoint is mutating and therefore protected by existing auth middleware.

Verification:

```bash
python -m pytest tests/test_constitution_registry.py tests/test_constitution_gate_script.py -q
# 7 passed

npm run verify:constitution
# PASS constitution_registry_tables
# PASS constitution_run_history_adapter
# PASS constitution_route_registration
# PASS constitution_registry_endpoints
# PASS mutating_auth_middleware_registered
# PASS mutating_methods_guarded: 116 mutating routes covered by middleware; 2 intentional exemptions
# PASS constitution_registry_tests
# PASS constitution_handoff_ledger
```

Next recommended slice:

1. Integrate decision/evidence writes into one low-risk existing flow, preferably scheduler lease refusal/dispatch or Lead fan-out, behind tests.
2. Add a read-only console surface for `/api/operator/constitution`.
3. Add a constitution registry seed/backfill path for existing ADR docs and capability IDs.

### 2026-08-09 — Codex autonomy decision trace slice completed

Status: completed; not committed yet.

Files changed:

- `services/control-plane/app/persistence/autonomous_attention_store.py`
- `tests/test_constitution_registry.py`

Implemented:

- `autonomous_attention_store.append_receipt(...)` now performs a best-effort constitution trace:
  - creates/updates an `evidence_registry` row pointing to `autonomy_attention_receipts`;
  - creates a canonical `decision_registry` row with `actor="autonomous_attention"`;
  - links the evidence row back to the decision ID.
- The original autonomy receipt remains the source of truth. Constitution indexing is best-effort and logs exceptions instead of preventing the autonomy receipt from being recorded.
- Added a focused test proving an autonomy receipt produces both evidence and decision records.

Why this improves AXON-X:

- VAXON/auto-attend decisions become traceable across the executive layer.
- Future audits can answer “why did the system dispatch/escalate/skip?” from a canonical decision record, while still preserving the original autonomy receipt.
- This directly supports constitution rules: evidence before action, every recommendation explains itself, and every decision is traceable.

Verification:

```bash
python -m pytest tests/test_constitution_registry.py tests/test_constitution_gate_script.py -q
# 8 passed

npm run verify:constitution
# PASS

python -m pytest tests/test_autonomous_attention_loop.py tests/test_autonomous_attention_recovery.py tests/test_autonomous_attention_concurrency.py -q
# 18 passed
```

Next recommended slice:

1. Add Lead-plan receipt indexing into Evidence Registry.
2. Add a read-only console surface for `/api/operator/constitution`.
3. Add a constitution registry seed/backfill path for existing ADR docs and capability IDs.

### 2026-08-09 — Codex Lead receipt evidence slice completed

Status: completed; not committed yet.

Files changed:

- `services/control-plane/app/workspace_agents/lead_plan_store.py`
- `tests/test_constitution_registry.py`

Implemented:

- `lead_plan_store.append_receipt(...)` now performs a best-effort Evidence Registry index.
- The original Lead receipt remains the source of truth; the constitution registry stores a pointer with:
  - `source_table="lead_plan_receipts"`;
  - `source_id=<receipt_id>`;
  - `source_ref={receipt_id, plan_id}`;
  - `workspace_id`;
  - the specific Lead receipt kind, e.g. `lead_plan_persisted`.
- Added a focused test proving a Lead receipt creates constitution evidence.

Why this improves AXON-X:

- Lead decomposition, fan-out, synthesis, and handoff receipts become visible to the executive evidence layer.
- VAXON can later build mission/executive briefings from durable Lead evidence instead of re-reading or paraphrasing chat.
- This supports the constitution principle that Executive Intelligence references execution and never duplicates execution.

Verification:

```bash
python -m pytest tests/test_constitution_registry.py tests/test_constitution_gate_script.py -q
# 9 passed

python -m pytest tests/test_lead_fan_out.py tests/test_lead_dana_report.py tests/test_lead_handoff_receipt.py -q
# 12 passed

npm run verify:constitution
# PASS
```

Next recommended slice:

1. Add a read-only console/API client surface for `/api/operator/constitution`.
2. Add a constitution registry seed/backfill path for existing ADR docs and capability IDs.
3. Link Lead plans to missions so mission progress can aggregate Lead/task/run/evidence records.

### 2026-08-09 — Codex console constitution surface slice completed

Status: completed; not committed yet.

Files added:

- `apps/console-web/src/api/constitution-api.ts`
- `apps/console-web/src/lib/constitution-overview-view.ts`
- `apps/console-web/src/lib/constitution-overview-view.test.ts`
- `apps/console-web/src/components/settings/ConstitutionOverviewPanel.vue`
- `apps/console-web/src/styles/settings/constitution-overview.css`

Files changed:

- `apps/console-web/src/lib/settings-section-route.ts`
- `apps/console-web/src/components/settings/OperatorSettingsSurface.vue`
- `apps/console-web/src/styles/settings/settings-feature-panels.css`

Implemented:

- Added a typed console API client for the constitution overview and registry list endpoints.
- Added a read-only Settings → Constitution panel.
- Added human-readable view helpers for count cards and recent registry summaries.
- Added a focused console test proving the view helpers render stable, readable summaries.

Why this improves AXON-X:

- Operators and agents can see the executive memory layer without shelling into SQLite.
- The UI is read-only, so visibility does not mutate planning or evidence state.
- Human-readable cards reduce the chance that task IDs, raw table names, or unparsed receipts are mistaken for meaningful status.

### 2026-08-09 — Codex constitution seed/backfill slice completed

Status: completed; not committed yet.

Files added:

- `services/control-plane/app/constitution_seed.py`

Files changed:

- `services/control-plane/app/persistence/constitution_registry_store.py`
- `services/control-plane/app/routes/constitution.py`
- `scripts/verify/check_constitution_gates.py`
- `tests/test_constitution_registry.py`

Implemented:

- Added stable `CAP-###` capability seeding for high-value constitution anchors, including evidence, mission, decision, ADR, debt, health, autonomous attention, Lead fan-out, runtime policy, console constitution surface, and verification.
- Added canonical ADR backfill from `docs/adr/ADR-*.md`.
- Added auth-covered endpoint:
  - `POST /api/operator/constitution/seed`
- Updated `verify:constitution` to require the seed endpoint and core capability anchors.
- Added tests proving capability seeds are idempotent and ADR markdown is parsed.

Important scope note:

- `docs/adr` and `docs/planning/ADR-*` both contain ADR-numbered files. This slice treats `docs/adr` as canonical for registry backfill to avoid silently overwriting different historical decisions with the same ADR number.

Why this improves AXON-X:

- The registry is useful immediately after deployment, rather than staying empty until enough runtime receipts accumulate.
- Blockers and decisions can reference stable capabilities such as `CAP-034 Autonomous attention loop`.
- Architecture decisions become queryable from the same constitution surface as missions and evidence.

### 2026-08-09 — Codex Lead-plan mission link slice completed

Status: completed; not committed yet.

Files changed:

- `services/control-plane/app/persistence/constitution_registry_store.py`
- `services/control-plane/app/workspace_agents/lead_plan_store.py`
- `tests/test_constitution_registry.py`

Implemented:

- Added `mission_for_lead_plan(...)` lookup in the constitution registry.
- `lead_plan_store.persist_plan(...)` now creates a best-effort mission for each persisted Lead plan.
- Lead receipt evidence now links to the matching mission when available.
- Added a test proving a persisted Lead plan creates a mission and links the `lead_plan_persisted` evidence row to that mission.

Why this improves AXON-X:

- Dana/Lead work now becomes durable mission state automatically.
- Mission progress can aggregate Lead plans, receipts, and later run evidence.
- If mission indexing fails, Lead planning still persists and logs the indexing failure rather than blocking work.

### 2026-08-09 — Codex handbook slice completed

Status: completed; not committed yet.

Files changed:

- `docs/HOW-TO-HANDBOOK.md`
- `docs/ops/agent-reports/axon-x-constitution-gap-audit-2026-08-09.md`

Implemented:

- Added an operator/agent handbook section for the AXON-X Constitution registries.
- Documented what each registry means, how it improves robustness, how agents should use it, where the console surface lives, and which verification commands prove it.

Why this improves AXON-X:

- Future agents can continue from a clear documented implementation trail instead of rediscovering intent from code.
- The operator gets an understandable mental model for the self-healing/evidence layer.

Verification after these four slices:

```bash
python -m pytest tests/test_constitution_registry.py tests/test_constitution_gate_script.py -q
# 13 passed

npm run verify:constitution
# PASS constitution_registry_tables
# PASS constitution_run_history_adapter
# PASS constitution_seed_capabilities
# PASS constitution_route_registration
# PASS constitution_registry_endpoints
# PASS mutating_auth_middleware_registered
# PASS mutating_methods_guarded
# PASS constitution_registry_tests
# PASS constitution_handoff_ledger

npm run test -w @axon-watch/console-web -- settings-section-route constitution-overview-view
# 2 files passed, 4 tests passed

python -m pytest tests/test_autonomous_attention_loop.py tests/test_autonomous_attention_recovery.py tests/test_autonomous_attention_concurrency.py tests/test_lead_fan_out.py tests/test_lead_dana_report.py tests/test_lead_handoff_receipt.py -q
# 30 passed
```

## Confidence

Confidence: 8/10

The audit is based on direct source/schema inspection and current DB table inspection. It may miss behavior implemented only in generated assets, external watch-service code, or runtime-only Claude/Cursor state not stored in this repo.

### 2026-08-10 — Codex watcher/action scheduler split slice completed

Status: completed; not committed yet.

Files changed:

- `services/control-plane/app/persistence/worker_scheduler_settings_store.py`
- `services/control-plane/app/workspace_agents/company_work_sources.py`
- `services/control-plane/app/workspace_agents/fleet_control.py`
- `services/control-plane/app/workspace_agents/lead_team_checkin.py`
- `services/control-plane/app/workspace_agents/scheduler.py`
- `services/control-plane/app/routes/worker_scheduler.py`
- `tests/test_workspace_agent_scheduler.py`
- `tests/test_worker_scheduler_routes.py`
- `tests/test_lead_team_checkin.py`
- `docs/HOW-TO-HANDBOOK.md`

Implemented:

- Split always-on watcher observation from worker/action dispatch.
- Added `watcher_scheduler_enabled` settings state, defaulting on while worker
  dispatch remains off by default.
- Added `AXON_WATCH_OBSERVATION_SCHEDULER` as the hard emergency brake for
  read-mostly watcher ticks.
- Added `run_observation_tick()` so CI/watch/delivery/fleet observation can run
  independently from Auto/Semi/Manual worker dispatch.
- Added `observation_only=True` handling to scheduled work sources so watcher
  ticks can reconcile/poll/escalate without creating file-size/autonomous repair
  tasks or dispatching fleet self-heal fixes.
- Changed Lead team check-in so failed Lead shifts are no longer skipped.
- Failed Lead shifts now become VAXON/operator attention receipts and do not
  auto-spam specialists with the wrong work.

Why this improves AXON-X:

- Company watchers act like a night watch: they keep observing and reporting even
  when the operator has paused autonomous action.
- Auto/Semi/Manual now cleanly describes action authority, not whether the system
  is allowed to notice problems.
- Team Leads cannot remain silently stuck in Error; their failure becomes an
  actionable VAXON/operator blocker with receipts.

Verification:

```bash
python -m pytest tests/test_workspace_agent_scheduler.py tests/test_worker_scheduler_routes.py tests/test_lead_team_checkin.py -q
# 34 passed
```
