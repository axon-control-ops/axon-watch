# MISSION-002 — AXON-X Platform Intelligence Audit

**Date:** 2026-08-02  
**Scope:** repository at `/home/edp/axon-nvme/repos/axon-watch`  
**Method:** static implementation inspection, configuration/contract review, route and persistence tracing, and non-mutating verification attempts. No product code was changed.  
**Confidence:** high for repository structure and implementation claims; medium for operational/UI claims because this audit did not take over the already-active local runtime or perform a clean, isolated end-to-end run.

## Evidence register

| ID | Evidence inspected |
| --- | --- |
| E1 | `README.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `project.axon.yaml` |
| E2 | Control-plane boot/routes: `services/control-plane/app/main.py`, `bootstrap.py`, `routes/` |
| E3 | Watch boot/API: `services/axon-watch/app/main.py`, `signals/`, `monitors/`, `delivery/`, `vault/` |
| E4 | Durable state: `persistence/run_store_sqlite.py`, `task_store.py`, `domain/run_state.py` |
| E5 | Orchestration: `workspace_agents/scheduler.py`, `worker_dispatch.py`, `worker_isolation.py`, `lead_*` |
| E6 | Runtime safety: `cli_runtime/approval_gate.py`, `safe_improvement/`, `auth/`, `internal_auth.py` |
| E7 | Product surfaces: `apps/console-web/src/main.ts`, `App.vue`, shell store/components, shared types |
| E8 | Desktop/runtime: `apps/console-desktop/README.md`, `src-tauri/src/runtime.rs`, `host/policy.rs` |
| E9 | Deployment/governance: `.github/workflows/`, `.env.example`, `infra/`, `scripts/verify/`, autonomy and ADR docs |
| E10 | Repository snapshot: 284 Python test modules, 315 Vue/TS test files, 216 declared HTTP/WebSocket routes, and 242,275 lines across tracked eligible text/source files; pre-existing concurrent edits and test processes were present |

Statements below are labelled **Observed**, **Inferred**, **Recommended**, or **Unknown**. “Implemented” means the code is present, not that it was proven live on this host today.

## Executive summary

**Observed.** AXON-X is a local-first, multi-workspace engineering control plane with an IDE-like console. It combines a Vue/Tauri operator surface, a FastAPI control plane, and a separate FastAPI monitoring service. It persists run, task, chat, memory, signal, delivery, and vault-related state locally, primarily in SQLite. It can route a bounded task through a Lead and specialist roster to CLI-backed coding agents, collect receipts, verify work, and prepare GitHub/CI delivery. [E1–E9]

**Observed.** Its architectural style is a pragmatic modular monolith plus a separated watcher: UI presents and steers; the control plane decides and dispatches; Watch detects, persists, and signals. HTTP/SSE are the actual integration mechanisms. The source has clear domain seams, but the control plane is large and operationally central. [E1–E7]

**Inferred.** AXON-X is beyond prototype: it has durable state machines, leases, path-aware tasks, isolation worktrees, CI remediation, a verification contract, token/mTLS support, and a native desktop wrapper. It is not yet an autonomous engineering operating system in the strong sense. It remains a supervised automation platform because mission history is projected rather than modeled, recovery cancels active work on restart, local SQLite is the coordination boundary, learning is not a closed feedback loop, and some high-risk read surfaces are unauthenticated. [E4–E9]

**Assessment.** The right next move is evolution, not replacement: close the security boundary, make mission/evidence durable and queryable, turn recovery from cancellation into resumability, and introduce explicit operational SLOs/observability before increasing unattended autonomy.

## System narrative: what actually happens

The intended hierarchy is Operator → VAXON → Lead → Specialists → REPORT → Operator. The implementation is close, with important shortcuts.

1. **Operator entry. Observed.** The web shell creates Pinia, loads bootstrap data before mount, then renders a five-region IDE/control-plane shell. It can also render vault, data, skills, mobile, settings, voice, and report-theater surfaces. SSE triggers light refreshes every 30/60 seconds and material-change updates. [E7]
2. **VAXON/KAIRO interpretation. Observed.** The operator talks through KAIRO conversation/voice endpoints. Intent classifiers, mission specification helpers, executive-context projection, thread/session memory, command routing, and deterministic report helpers run inside the control plane. VAXON is not a separately scheduled process or durable mission engine; ADR-009 explicitly makes it an executive projection over existing plans, runs, handoffs, receipts, and memory. [E2, E5, E9]
3. **Direct versus executive routes. Observed.** A request may become a consultative CLI turn, an explicit shell command, a run, a Lead plan/fan-out/replan, or a named specialist route. Therefore not every operator action passes through VAXON and a Lead. That is useful responsiveness, but it means the stated hierarchy is a preferred orchestration path, not an invariant. [E2, E5, E6]
4. **Lead. Observed.** A Lead is an `on_demand` roster role. Lead APIs create an ordered plan/DAG, materialize leased tasks, dispatch dependency-ready specialist work, replan obsolete work, and synthesize results. The continuous scheduler explicitly skips Lead roles. [E5]
5. **Specialists. Observed.** Watcher, frontend, backend, and integrations roles may be `always_on` or `continuous`, but the scheduler is controlled by an environment brake and a persisted UI setting. A worker requires a leased task, creates a disposable isolation root, invokes the Lane B/CLI runtime with an execution tier, streams progress to an employee thread, records run receipts, and updates the task. [E4–E6]
6. **Verification and delivery. Observed.** The verifier runs contract-defined commands, scans changed files, enforces path/secret policy, and has a critical-review contract. Delivery can create branches/draft PRs and poll CI; CI webhooks/remediation persist outcomes. These are implemented pathways, not proof that every task traverses them. [E5, E6, E9]
7. **REPORT back to operator. Observed.** Operator briefing, fleet health, evidence, run history, task board, and KAIRO report helpers aggregate persisted records and Watch output. The executive report is therefore a projection with receipts, not an independent decision record. [E2, E4, E7]

## Architecture, boundaries, and operations

| Area | Observed implementation | Assessment |
| --- | --- | --- |
| Console | Vue 3, Pinia, Vite, Monaco, xterm; a large `shell.ts` plus smaller slices | Strong product breadth; central store is a maintained hotspot (4,085 lines, waiver to 2026-08-30). [E7, E9] |
| Control plane | FastAPI, 17 router groups, 150+ public API declarations, chat, plans, runs, agents, workspaces, vault proxy | Correct ownership direction but a broad process-level trust and failure domain. [E2] |
| Watch | FastAPI API plus connector/monitor/signal/delivery/tunnel/vault modules | Meaningfully independent service, although its startup is synchronous and uses deprecated FastAPI `on_event`. [E3] |
| Contract boundary | TS shared types and fixtures; Python DTOs duplicated around routes | Good intent; not a generated cross-language schema, so drift remains possible. [E7, E9] |
| Communication | Control plane → Watch HTTP with optional token/mTLS; browser → CP HTTP/SSE; Watch SSE | Simple local-first topology; no durable message bus or command queue. [E2, E3, E6] |
| State | SQLite WAL, per-service databases, chat/runs/history/tasks/memory/receipts/signals | Excellent thin-slice durability; SQLite writer and host availability constrain multi-node scale. [E3, E4] |
| Memory | operator memories, KAIRO session/participant/turn memory, host context; executive mission memory is projected | Useful short/medium-term memory; no governed semantic retrieval, provenance graph, retention policy, or learning loop. [E4, E5, E9] |
| Tools | Cursor/Codex/Claude CLI adapters, terminal PTY, Git/GitHub, research, Azure STT/TTS, Sentry/PostHog/Supabase/email/tunnel | Broad integration fabric; availability depends on host binaries, credentials, quotas, and mutable environment. [E3, E5, E6] |
| Startup | Watch starts, CP reconciles runs then scheduler, console starts; scripts fail fast and roll back bootstrap stack | Good bootstrap ergonomics; CP restart intentionally cancels in-flight workers rather than resumes. [E2, E3, E9] |
| Shutdown/recovery | scheduler stop, process registry cancellation, stale and restart reconciliation | Safe against ghost work, weak for long-running continuity. [E2, E5] |
| Deployment | local, user/system systemd, Caddy template, Docker skeleton, Tauri frozen sidecars | Dedicated-server direction is credible; production packaging and proxy/mTLS proof are incomplete. [E8, E9] |

## Agent architecture

**Observed.** “Agents” are not independent services. They are configured identities, prompts, scopes, and execution paths inside one control plane. The default roster shape is Lead, Watcher, Frontend, Backend, Integrations; the checked-in configuration contains several named company rosters. [E5]

| Agent | Purpose/lifecycle | Inputs and outputs | Permissions/limits/escalation |
| --- | --- | --- | --- |
| Operator | Starts work, reviews, approves, stops, engages plans | UI/voice commands; receives briefings, evidence, approvals | Human authority remains required for protected/irreversible actions. [E7, E9] |
| VAXON/KAIRO | Executive conversation, mission framing, contextual reporting | Conversation, memories, plans, receipts; emits replies/route proposals/report text | Projection, not durable autonomous executive; must label evidence state. [E5, E9] |
| Lead | Decompose, assign, replan, synthesize | Goal, roster, existing tasks/runs; emits plan, tasks, handoffs, receipts | On demand; scheduler skips it; cannot by itself make delivery safe. [E5] |
| Watcher | Observe signals and investigate | Watch/CI/runtime sources; emits signals, tasks, reports | Continuous only when explicitly enabled; not a full incident commander. [E3, E5] |
| Frontend/Backend/Integrations | Implement assigned bounded work | Leased task, role prompt, isolated checkout; emits diff, receipts, delivery state | Uses CLI runtime; full tool access is consent/phase-gated; path/task scope must pass verifier. [E5, E6] |
| Verifier | Independently run contract checks and assess delivery | Changed paths, project contract, command plan; emits pass/fail evidence | Runs shell contract commands in workspace; not a separate trust domain/process. [E5, E6] |
| CI remediator | Ingest failed workflow events, classify, dispatch repair, poll outcome | Signed webhook/CI result; emits repair receipts | Narrow GitHub path, no demonstrated general incident remediation. [E2, E5] |
| Desktop host | Expose narrow OS-context actions | Host snapshot/action requests; emits host receipts | Rust policy auto/confirms/denies actions; sensors/pairing/keyring are explicitly stubs. [E8] |

**Missing capabilities.** No independently durable mission executive, no separate verifier identity or isolated verifier infrastructure, no capability tokens per agent/tool, no organization-wide conflict resolver, no resource/cost governor, no formal incident commander, and no long-horizon evaluation agent. [E5, E6, E9]

## Platform capability matrix

| Capability | Status | Evidence and qualification |
| --- | --- | --- |
| IDE shell/editor/terminal | Implemented | Monaco, xterm, explorer and Tauri wrapper are in product. [E7, E8] |
| Run state/history | Implemented | Explicit phases, SQLite run/history tables. [E4, E7] |
| Task ledger/leases/dependencies | Implemented | Leases, attempt limits, dependencies, path fields. [E4, E5] |
| Lead planning/fan-out/replan | Implemented | Dedicated APIs/services; Lead is on demand. [E2, E5] |
| Specialist CLI execution | Implemented | Cursor/Codex/Claude adapters and worker dispatch. [E5, E6] |
| Disposable worker isolation | Implemented | Per-run worktree/clone isolation. [E5] |
| Approval gates | Implemented | Run phase/full-access and exact-effect policies. [E6] |
| Safe self-improvement | Experimental | Default-off, isolated, exact-approval contract; reserved effects do not mutate live targets. [E6, E9] |
| CI repair/draft PR flow | Partial | Implemented workflow, but delivery depends on external GitHub/runtime readiness. [E5, E9] |
| Watch connectors/signals | Implemented | Canonical signal/inbox/event store and connector probes. [E3, E7] |
| Delivery receipts/channels | Partial | Inbox, webhook, Slack, push, desktop adapters; enrollment/config dependent. [E3] |
| Sentry/PostHog/Supabase monitoring | Partial | Specific DashPro monitors and caches, not a general telemetry platform. [E3] |
| Research | Partial | SearXNG/Google/DDG path and cache/receipts, no research quality evaluator. [E5, E9] |
| Vault | Implemented with critical access defect | Encryption/session/export/import exist; GET secret/export authorization is absent. [E3, E6] |
| Voice/STT/TTS | Partial | Azure integrations and voice deck exist; accessibility/reliability proof is incomplete. [E2, E7] |
| Desktop host context | Experimental | Narrow policy works; sensors, pairing, keyring remain stubbed. [E8] |
| Multi-project awareness | Partial | Workspace catalog/rosters/bindings exist; shared host/runtime capacity and global governance remain weak. [E5, E9] |
| Organizational memory | Partial | Records exist, but no evidence graph or lifecycle management. [E4, E5] |
| Knowledge graph | Experimental | Operator brain projection/UI, no canonical graph store/query service. [E2, E7] |
| Autonomous recovery | Partial | Stale reconciliation and retry exist; restart cancels active work. [E2, E5] |
| Observability/SLOs | Partial | Health, runtime summary, signals, logs; no metrics/tracing/alert SLO fabric. [E2, E3, E9] |
| Scalability/HA | Missing | SQLite/local processes; no queue, replicas, leader election, backups/restore drill evidence. [E3, E4] |
| Mobile control | Experimental | Compact browser surface/tunnel; not a hardened mobile control plane. [E7, E9] |
| Production deployment | Partial | systemd/Caddy templates and docs; Docker is explicitly placeholder and live hardening is deployment-dependent. [E9] |

## Autonomy assessment

Scores are engineering judgement from repository evidence, not measured production reliability.

| Question | Score | Assessment |
| --- | ---: | --- |
| Plan | 70% | Lead plans/DAGs and task materialization are real, but mission is not first-class durable state. |
| Research | 45% | Search and receipts exist; source quality, synthesis, citation and evaluation controls are thin. |
| Learn | 25% | Memories and reports are stored/projected; no measured lesson-to-policy loop. |
| Delegate | 70% | Roster, named routing, leases, fan-out and capacity gates are strong. |
| Recover | 40% | Stale/retry handling exists; CP restart cancels workers rather than checkpoints/resumes. |
| Monitor | 65% | Connector, monitor and signal subsystems are substantive but configuration-specific. |
| Coordinate | 60% | Dependencies and path bounds exist; no durable event workflow or cross-project arbitration. |
| Review/verify | 65% | Contract verifier, critical review and CI flow exist; verifier executes in the same control-plane trust boundary. |
| Improve itself | 25% | Safe-improvement is deliberately experimental/default-off. |
| Document itself | 55% | ADRs, contracts, how-tos and evidence logs are extensive, but drift is visible. |

**Primary blockers to greater autonomy.** Security of read access; restart/resume semantics; shared local coordination; lack of mission/evidence ledger; absence of a trusted verifier boundary; no resource/spend/SLO governor; external-runtime quota sensitivity; and incomplete operational documentation. [E4–E10]

## JARVIS / Executive OS gap analysis

**Observed.** ADR-009 already correctly defines VAXON as the executive identity layered over the existing platform, not a new swarm. [E9]

**Gap.** A true executive OS needs a durable, queryable mission portfolio, explicit decision records, confidence/calibration history, organization-wide resource awareness, and a safe authority model. AXON-X today projects most of these from runs, plans, tasks, briefings, and conversation memory. Projection is excellent for an operator view but insufficient for executive continuity, audit, or strategic learning.

**What should not be replaced.** Retain the run state machine, task ledger, Lead fan-out, worker isolation, receipts, shared types, Watch signal model, and locked shell. They are leverage points. Build the executive layer as append-only mission/decision/evidence references that link to those records rather than duplicating execution.

## UI/UX review

**Observed.** The console has an unusually rich command center: IDE workbench, task board, fleet health, briefing, attention stack, company roster, connectors, brain graph, voice deck, vault, data, skills, desktop/mobile modes, and live updates. Components include status/alert roles, labels, expanded-state semantics, focus-visible rules, responsive selectors, and reduced-motion handling. [E7]

**Inferred.** This breadth risks cognitive overload. The shell gives operator, developer, executive, voice, incident, and administration functions equal visual opportunity. The large shell store and many shell components indicate a powerful but increasingly coupled interaction model. [E7, E9]

**Unknown.** This audit did not run a clean browser session, keyboard-only test, screen-reader test, contrast measurement, mobile device test, or performance profile. Visual hierarchy and actual interaction latency therefore require empirical validation.

## Engineering, reliability, and security review

**Strengths observed.** Explicit run transitions; SQLite WAL/busy timeout; schema migrations; failure receipts; startup/stale reconciliation; bounded scheduler defaults; path-aware tasks; isolated worktrees; an approval model; protected CI workflow; test inventory; guardrails; and architecture/ADR discipline. [E4–E9]

**Debt observed.** The control plane has many feature modules and broad route surface; `shell.ts` is 4,085 lines with an active waiver; multiple source files exceed normal limits under ratchets; there are duplicated top-level Python `app` packages requiring a special test runner; Python dependencies are not declared in `pyproject.toml`; frontend dependencies use mutable `latest`; and Watch still uses deprecated startup API. [E2–E10]

### Confirmed defects

1. **Critical — unauthenticated vault disclosure on remote control plane. Observed.** `MutatingAuthMiddleware` authenticates only POST/PUT/PATCH/DELETE. `GET /api/vault/secrets/{secret_id}` returns decrypted secret data when the process vault is unlocked, and `GET /api/vault/export/csv` exports decrypted secrets. Those routes have no route-specific auth. This bypasses the documented remote `local_token` posture. [E6: `auth/middleware.py`, `routes/vault_http.py`, `vault/routes.py`; E3: `vault/api.py`]
2. **High — Watch confidential reads are also unauthenticated at the service boundary. Observed.** `InternalServiceTokenMiddleware` gates only mutating routes; Watch exposes `GET /internal/watch/vault/secrets/{id}` and CSV export. The Caddy example hides Watch, which reduces exposure, but that proxy restriction is deployment convention rather than an in-process guarantee. [E3, E6, E9]
3. **Medium — active worker work is not resumable across a control-plane restart. Observed.** Startup reconciliation moves non-terminal employee runs through paused to cancelled. This protects truth but loses progress and wastes external runtime time. [E2: `runs/restart_reconcile.py`]
4. **Medium — arbitrary shell execution is blacklist-based. Observed.** Explicit `run …` commands are passed to `subprocess.run(..., shell=True)` after blocking a short pattern list. Auth mitigates remote exploitation, but blacklist parsing is an unsuitable long-term authorization boundary for a powerful operator shell. [E6: `chat/shell_command.py`]

### Likely defects / risks needing confirmation

- **High:** Separate process-level services share host credentials and local state paths; a compromised CP can invoke Watch or local tools. Confirm with a threat-model and deployment test. [E3, E6, E9]
- **Medium:** Full test verification was not obtained during this audit because concurrent work left long-running test processes and a moving worktree. Establish a clean baseline before any readiness claim. [E10]
- **Medium:** `.env.example` defaults auth to `placeholder`; remote mode attempts to force token behavior, but a misclassified public route or proxy can still expose reads. Validate an external black-box matrix. [E6, E9]
- **Medium:** Runtime/process registries are in-memory while state is SQLite; restart semantics cannot recover process identity. Confirm through kill/restart drills. [E4–E6]
- **Low:** `requirements.txt` contains `httpx2` while `pyproject.toml` has no runtime dependency declaration. Confirm installation reproducibility in a clean environment. [E9]

## Future architecture

| Horizon | Recommendation | Reason, benefit, risk/complexity, dependencies |
| --- | --- | --- |
| 0–30 days | Close read authorization and export exposure | Highest-impact safety gap; low/medium complexity; requires a route policy and tests. [E6] |
| 0–30 days | Introduce a clean, repeatable audit/deployment profile | Makes current claims reproducible; low complexity; requires isolated test/runtime environment. [E9, E10] |
| 30–90 days | Add an append-only mission/decision/evidence ledger | Makes VAXON queryable/auditable without replacing runs/tasks; medium complexity; link existing IDs. [E4, E5, E9] |
| 30–90 days | Add durable workflow checkpoints/leases for resume | Replace cancellation-only recovery; medium/high complexity; process/CLI capability assessment needed. [E2, E5] |
| 30–90 days | Split policy enforcement from UI/control-plane code | Capability and route policy become testable and consistent; medium complexity. [E2, E6] |
| 3–12 months | Extract durable work orchestration only when warranted | Queue/workflow engine enables HA, retries and audit; high complexity; preserve current API contracts. [E1, E4] |
| 3–12 months | Build observability and resource governance | Metrics, traces, cost/credit/RAM quotas and SLOs are prerequisites to unattended scale; high complexity. [E5, E9] |
| 3–12 months | Make executive intelligence a governed projection service | Knowledge graph, learning/evaluation, portfolio health—grounded in the ledger; high complexity. [E4, E5, E9] |

## Recommendations

Each item cites supporting evidence IDs. Priority: P0 immediate, P1 next, P2 planned.

### Top 10 quick wins

1. **P0** Require authenticated, step-up access for every vault read/export and add denial tests. [E3, E6]
2. **P0** Gate all Watch vault reads with service identity, not only mutations. [E3, E6]
3. **P0** Replace the generic `run` shell blacklist with a command registry/structured argv allowlist. [E6]
4. **P0** Add a CI test that enumerates every sensitive GET route against anonymous remote posture. [E2, E3, E6]
5. **P1** Make `AXON_WATCH_AUTH_MODE=local_token` the non-test default and fail public boot without it. [E6, E9]
6. **P1** Mark the July readiness claims superseded where Gate 3/4 code now exists. [E5, E9]
7. **P1** Produce one clean, pinned dependency installation path from `pyproject.toml`/lockfiles. [E9]
8. **P1** Replace Watch `@app.on_event` with lifespan and test graceful shutdown. [E3]
9. **P1** Surface restart cancellation/resume limitations in the operator UI before a restart action. [E2, E7]
10. **P1** Expire the shell-store waiver with a tracked extraction milestone and owner. [E7, E9]

### Top 25 architectural improvements

1. P0 Centralize route sensitivity policy. [E2, E3, E6]
2. P0 Introduce capability-scoped auth tokens for operator, CP, Watch, and tools. [E3, E6]
3. P1 Create an append-only mission ledger linked to plan/task/run/receipt IDs. [E4, E5, E9]
4. P1 Create a decision ledger with authority, rationale, expiry, and outcome. [E5, E9]
5. P1 Model evidence as immutable typed references, not report text alone. [E4, E7, E9]
6. P1 Add a workflow checkpoint abstraction above subprocess state. [E2, E5]
7. P1 Separate command authorization from natural-language intent parsing. [E2, E6]
8. P1 Make verifier execution a separately scoped worker/service. [E5, E6]
9. P1 Add a durable outbox/inbox for CP↔Watch commands/events. [E2, E3]
10. P1 Version HTTP DTOs and generate/validate cross-language contracts. [E2, E7]
11. P1 Establish a repository-wide configuration schema and validation command. [E1, E9]
12. P1 Separate workspace identity from host filesystem identity. [E5, E8]
13. P1 Define a formal agent capability manifest per role. [E5, E6]
14. P1 Add global resource, spend, and concurrency governor. [E5, E9]
15. P1 Persist runtime provider/usage snapshots as evidence. [E5, E7]
16. P1 Standardize idempotency keys for all effecting routes. [E2, E3]
17. P1 Introduce explicit incident lifecycle records. [E3, E7]
18. P2 Move SQLite access behind repository interfaces with migration/backup ownership. [E3, E4]
19. P2 Evaluate a workflow engine only for long-running cross-process missions. [E1, E2]
20. P2 Add a read-optimized portfolio projection store. [E4, E5]
21. P2 Add governed semantic retrieval with source provenance. [E4, E5]
22. P2 Add policy-as-code tests to every authority expansion. [E6, E9]
23. P2 Establish service-level threat boundaries for desktop sidecars. [E8, E9]
24. P2 Support leader election/HA only after state and queue abstraction. [E3, E4]
25. P2 Publish a canonical architecture decision map linking ADRs to modules. [E1, E9]

### Top 25 engineering improvements

1. P0 Add anonymous-read security tests for all vault endpoints. [E3, E6]
2. P0 Remove `shell=True` from operator execution or constrain it to audited argv templates. [E6]
3. P1 Move Python dependencies into `pyproject.toml` and pin/lock them. [E9]
4. P1 Replace frontend `latest` dependencies with reviewed versions and lockfile enforcement. [E9]
5. P1 Finish shell-store slice extraction and remove waiver. [E7, E9]
6. P1 Establish module size/dependency budgets for CP feature clusters. [E2, E9]
7. P1 Rename/split top-level Python packages to avoid isolated-import test runner complexity. [E9]
8. P1 Convert Watch lifecycle events to lifespan. [E3]
9. P1 Add database migration versioning/checksum and downgrade/restore policy. [E4]
10. P1 Add structured logs with run/task/mission/correlation IDs. [E2–E5]
11. P1 Add OpenTelemetry traces across UI, CP and Watch. [E2, E3]
12. P1 Make external client timeouts/retries/circuit breakers uniform. [E3, E5]
13. P1 Add property tests for state transitions and task leases. [E4]
14. P1 Add contract fuzz tests for public request schemas. [E2, E3]
15. P1 Add test isolation that never shares `.local/state`. [E4, E10]
16. P1 Publish a clean-baseline verification artifact per merge. [E9, E10]
17. P1 Test process kill/restart/partial-write recovery. [E2, E5]
18. P1 Add secret redaction to logs, receipts, failure excerpts and frontend stores. [E3, E6]
19. P1 Add SBOM/dependency vulnerability scanning. [E9]
20. P1 Add static analysis for subprocess/env/file-path sinks. [E5, E6]
21. P2 Add performance budgets for bootstrap, stream latency and large rosters. [E7, E9]
22. P2 Replace source-file ratchets with ownership plus complexity/coupling measures. [E7, E9]
23. P2 Add database backup/restore and corruption drills. [E3, E4]
24. P2 Build platform integration test fixtures for every connector. [E3, E9]
25. P2 Publish deprecation/removal lifecycle for bootstrap-only code. [E1, E3]

### Top 25 UX improvements

1. P0 Put auth/session and vault-lock status in the global attention model. [E6, E7]
2. P0 Warn clearly that restart cancels active workers. [E2, E7]
3. P1 Make Mission, IDE, Incident, and Admin explicit modes with focused defaults. [E7]
4. P1 Provide one “next best verified action” with its evidence and authority. [E5, E7]
5. P1 Keep direct commands visually distinct from Lead-orchestrated missions. [E2, E5, E7]
6. P1 Show every task’s path bounds, lease, dependency and attempt budget in the board. [E4, E7]
7. P1 Show an evidence-state badge (planned/dispatched/observed/verified/approved). [E9]
8. P1 Add a compact executive timeline across plan/task/run/CI/decision. [E4, E5, E7]
9. P1 Add clear runtime cost/credit/RAM capacity indicators. [E5, E7]
10. P1 Make automatic versus human-required actions unmistakable. [E6, E7]
11. P1 Give sensitive read/export actions step-up, explanation and audit feedback. [E6, E7]
12. P1 Add a recovery center for restart, stale lease, retry and orphaned work. [E2, E5, E7]
13. P1 Add a filterable cross-workspace portfolio health view. [E5, E7]
14. P1 Add empty/error/offline states for every external integration. [E3, E7]
15. P1 Add keyboard-command documentation and command safety previews. [E6, E7]
16. P1 Test full keyboard navigation and focus restoration. [E7]
17. P1 Test screen-reader labels/live regions with real assistive tech. [E7]
18. P1 Measure contrast and motion alternatives in the holographic theme. [E7]
19. P1 Provide reduced-information mode for incident response. [E7]
20. P1 Make mobile mutation unavailable until remote security posture is verified. [E7–E9]
21. P2 Add explanation views for signal ranking and autonomous attention. [E3, E7]
22. P2 Add a replayable mission report theater sourced from ledger data. [E5, E7]
23. P2 Make roster health show capability/credential readiness, not only status. [E5, E7]
24. P2 Add operator preference onboarding and persistence transparency. [E4, E7]
25. P2 Instrument user flows to validate cognitive-load assumptions. [E7]

### Top 25 autonomy improvements

1. P0 Block unattended operation until vault/read authorization is closed. [E3, E6]
2. P0 Require a clean verified baseline before enabling continuous workers. [E9, E10]
3. P1 Make every autonomous action originate from a mission/task/evidence ID. [E4, E5]
4. P1 Add policy-checked autonomy levels by workspace and effect type. [E5, E6]
5. P1 Make Lead planning mandatory for multi-step/high-risk work. [E5]
6. P1 Require acceptance criteria and verifier plan before dispatch. [E4, E5]
7. P1 Record confidence, uncertainty, and assumptions as typed receipts. [E5, E9]
8. P1 Add independent verifier model/process selection. [E5, E6]
9. P1 Add bounded retry strategies classified by failure cause. [E2, E5]
10. P1 Add resource/credit/spend brake before each dispatch. [E5, E9]
11. P1 Add cooldown and incident escalation rules for repeated failures. [E3, E5]
12. P1 Resume checkpointed work rather than cancelling after CP restart. [E2, E5]
13. P1 Require source/citation quality policy for research-derived tasks. [E5]
14. P1 Turn mission outcomes into reviewed lessons with provenance. [E4, E5]
15. P1 Add counterfactual/evaluation datasets for planner changes. [E6, E9]
16. P1 Add cross-workspace conflict and priority arbitration. [E5]
17. P1 Separate execution, verification, approval and publication identities. [E5, E6]
18. P1 Require human approval for authority expansion and secret/production effects. [E6, E9]
19. P1 Add post-deploy observation and automatic rollback *recommendation* evidence. [E3, E5]
20. P1 Create a trustworthy no-op/decision-only task policy. [E4, E5]
21. P2 Maintain calibration metrics: predicted versus actual outcome/confidence. [E4, E5]
22. P2 Build a governed knowledge graph from mission/evidence links. [E4, E5]
23. P2 Support simulations before policy changes. [E6, E9]
24. P2 Establish multi-day mission supervision handoff protocol. [E5, E9]
25. P2 Define an autonomy release ladder with reversible exit criteria. [E6, E9]

### Top 25 reliability improvements

1. P0 Protect vault GET routes. [E3, E6]
2. P0 Add restart-drill acceptance tests. [E2, E5]
3. P1 Persist process/checkpoint identity for resumable runs. [E2, E5]
4. P1 Add command/event idempotency and deduplication universally. [E2, E3]
5. P1 Add durable outbox retry with dead-letter handling. [E2, E3]
6. P1 Add connector health budgets and stale-data age indicators. [E3]
7. P1 Add circuit breakers for runtime, Watch and CI providers. [E3, E5]
8. P1 Add monitor probe rate limits/backoff per provider. [E3]
9. P1 Make scheduler capacity account for RAM, credits and tool quota. [E5]
10. P1 Add backup encryption, restore drills and DB integrity checks. [E3, E4]
11. P1 Add graceful service drain semantics. [E2, E3]
12. P1 Add bounded SSE reconnect/backpressure and subscriber metrics. [E2, E7]
13. P1 Add worker heartbeat plus meaningful-progress watchdog metrics. [E5]
14. P1 Surface lease expiry before it causes loss of work. [E4, E7]
15. P1 Add filesystem/worktree cleanup reconciliation and quota. [E5]
16. P1 Add dependency availability/readiness truth beyond HTTP 200. [E2, E3]
17. P1 Test provider outage, partial response and credential rotation paths. [E3, E5]
18. P1 Alert on repeated verifier false failures and execution timeouts. [E5]
19. P1 Run watchdog processes outside the CP worker process. [E2, E5]
20. P1 Exercise actual systemd/Caddy/mTLS deployment in CI or staging. [E8, E9]
21. P2 Introduce queue/workflow durability for long-running jobs. [E1, E2]
22. P2 Add HA/failover only after state ownership is explicit. [E3, E4]
23. P2 Define service SLOs/error budgets and alert routing. [E2, E3]
24. P2 Maintain chaos/recovery scenario corpus. [E2–E5]
25. P2 Add production configuration drift detection. [E9]

### Top 25 documentation improvements

1. P0 Correct vault security and remote-read posture documentation. [E3, E6, E9]
2. P0 Update `AXON-X-AUTONOMY-READINESS.md` for implemented Gate 3/4 work. [E5, E9]
3. P1 Publish this architecture as current-state versus target-state diagrams. [E1–E5]
4. P1 Document the actual direct-command bypasses of the executive hierarchy. [E2, E5]
5. P1 Define VAXON’s projected versus persisted state explicitly. [E5, E9]
6. P1 Publish API authentication matrix covering all reads/writes. [E2, E3, E6]
7. P1 Publish agent role/capability/escalation matrix. [E5]
8. P1 Document all run/task/mission evidence-state transitions. [E4, E9]
9. P1 Document restart, stale-run, cancellation and recovery operator procedures. [E2, E5]
10. P1 Document verifier trust limits and shell-command risk. [E5, E6]
11. P1 Document vault threat model, session lifetime and export behavior. [E3, E6]
12. P1 Document configuration precedence and required remote settings. [E1, E9]
13. P1 Publish an environment compatibility/support matrix. [E8, E9]
14. P1 Document connector ownership, data freshness and failure behavior. [E3]
15. P1 Establish a living dependency/version policy. [E9]
16. P1 Add deployment runbooks with tested rollback and restore steps. [E8, E9]
17. P1 Explain test-runner isolation caused by duplicate Python packages. [E9]
18. P1 Publish a clean verification protocol and evidence retention policy. [E9, E10]
19. P1 Add data retention/deletion and privacy policy for chats, voice and memories. [E4, E5]
20. P1 Define incident severity, ownership and communication rules. [E3, E7]
21. P2 Create ADRs for auth read policy, mission ledger and checkpoint recovery. [E6, E9]
22. P2 Add architecture decision traceability to code owners/modules. [E1, E9]
23. P2 Publish accessibility and performance test results, not intentions. [E7]
24. P2 Create a public internal glossary for VAXON/KAIRO/Lead/Watch/REPORT. [E1, E9]
25. P2 Establish quarterly evidence-driven autonomy reassessment. [E9, E10]

## Autonomous OS readiness

| Dimension | Readiness | Why |
| --- | ---: | --- |
| Executive AI | 50% | Strong projection/persona and briefing; no durable mission/decision portfolio. |
| Mission Planning | 70% | Lead plan/DAG/task fan-out are substantive. |
| Knowledge Graph | 30% | Brain projection and memories, no canonical governed graph. |
| Organizational Memory | 45% | Multiple stores, limited provenance/retention/retrieval governance. |
| Evidence Engine | 65% | Receipts, run history, verifier/CI evidence; not immutable unified ledger. |
| Decision Engine | 40% | Policies and routing exist; decisions are not a first-class audited object. |
| Project Health | 65% | Watch signals, connectors, monitors and runtime summaries. |
| Mission Learning | 25% | Stored context, no measured feedback/evaluation loop. |
| Continuous Improvement | 25% | Safe-improvement is bounded, default-off, reserved effects. |
| Autonomous Recovery | 40% | Detect/cancel/retry, but not checkpoint/resume. |
| Executive Briefings | 70% | Rich aggregation/UI/voice; correctness depends on projected inputs. |
| Operator Dashboard | 75% | Broad and polished surface; needs empirical usability/accessibility evidence. |
| Multi-project awareness | 55% | Catalog/rosters/bindings work; global governance/capacity/priority are immature. |
| Learning from history | 25% | No formal lessons/evaluations/calibration loop. |

**Overall:** **48% readiness for a supervised autonomous engineering OS; 25% readiness for unattended multi-project engineering autonomy.** The lower number is intentionally constrained by the confirmed vault-read exposure, cancellation-only recovery, shared local control plane, and absence of a durable mission/evidence/learning layer.

## Closing narrative

AXON-X already has the hard-won middle of an autonomous engineering platform: it can name and route work, persist operational truth, isolate coding attempts, observe projects, verify against contracts, and put the operator in a rich command surface. Its future does not require a rewrite or a new agent swarm. It requires making the present seams trustworthy under failure, explicit under audit, and governed under growing authority.

The first Blueprint chapter should therefore be **Trustworthy Executive Continuity**: secure every read and effect; preserve mission, decision, and evidence lineage; and resume bounded work safely. Once those foundations are established, AXON-X can turn VAXON from an excellent executive projection into a dependable executive operating system.
