# Axon-X Autonomy Master Plan

**Purpose:** Turn the readiness assessment into a strict, ordered build plan.  
**Source of truth:** `docs/AXON-X-AUTONOMY-READINESS.md`  
**Created:** 20 July 2026  
**Target:** Bounded autonomy so any bound workspace can work in its own project/app, proven first on DashPro, then a secure Axon-X mobile control plane

---

## Mission

Build a system where:

1. Workspaces can work on/in their own projects and apps without a human babysitting every step.
2. Axon-X can build and operate its own mobile control plane under the same safety rules.
3. Dangerous actions stay blocked unless a human explicitly approves them.

This is **bounded autonomy**, not unlimited power. DashPro is the first proving ground for the multi-workspace rule; the same controls must apply to every bound workspace (including `workspace_axon_watch`).

---

## North-star outcome

```text
Approved goal
  → Lead divides work
  → One leased task
  → Isolated branch / worktree
  → Specialist implements
  → Mandatory tests pass
  → Independent AI review
  → Draft pull request
  → CI watch + limited repair
  → Staging deploy + health check
  → Human gate for production risk
  → Release or automatic rollback
  → Receipt for every step
```

Until that loop is proven, continuous workers must not freely edit any live
bound workspace checkout (DashPro is the highest-risk example today).

---

## Non-negotiable rules

| Rule | Why |
| --- | --- |
| Order is mandatory | Later stages depend on earlier safety |
| No live shared checkout for continuous workers | Prevents mixed, unowned changes |
| No anonymous mutation APIs | Remote and mobile control must be safe |
| Tests are chosen before work starts | Workers cannot grade their own homework |
| Pull requests before merge | Dirty folders are not a delivery method |
| Production stays human-gated first | Secrets, store promotion, and irreversible actions remain protected |
| Pause before expand | Do not add autonomy while dirty live canary trees are unsorted |
| Post-receipt Critical Review Clause | Every agent (incl. Verifier when Gate 6 lands) ends with rewrite + `Confidence: N/10`; missing confidence fails closed |
| Workspace-scoped platform capability | DashPro is Wave A canary; the same loop applies to every bound `workspace_id` |

---

## Current starting point (from readiness)

| Metric | Value |
| --- | --- |
| Overall safe production autonomy | ~35–38% |
| Supervised operator maturity | ~68% |
| Safe task → PR loop | ~25–38% |
| Secure mobile control plane | ~10% |
| Immediate hazard | DashPro live checkout has a large mixed change set |
| Immediate blocker | Usage limits + shared capacity + restart cancellations |

---

## Timeline overview

These calendar ranges are **rough planning guesses**, not commitments. They assume
parallel engineering, available Cursor capacity, and no major scope expansion.

| Phase | Gates | Focus | Rough calendar guess |
| --- | --- | --- | ---: |
| **Stabilize** | 0–1 | Stop damage, restore trust | ~Week 1 |
| **Contain** | 2–3 | Auth + isolation | ~Weeks 2–4 |
| **Orchestrate** | 4–7 | Tasks, Lead, verify, review | ~Weeks 4–8 |
| **Publish** | 8–10 | PRs, CI loop, fair scheduling | ~Weeks 8–12 |
| **Prove** | 11–12 | Staging + DashPro canary | ~Weeks 12–16 |
| **Remote** | 13–14 | Mobile PWA + bounded production | ~Weeks 16–20 |

Parallel work is allowed only when earlier gates are green and the debt rules below are met.

---

## Debt gate (must stay green)

Do not start the next major gate while any of these are true:

- continuous workers are mutating a shared live checkout;
- autonomy-critical tests are red;
- review-ready backlog is uncontrolled;
- zombie `executing` runs exist;
- Cursor usage is exhausted with no recovery policy;
- anonymous network clients can mutate the control plane.

---

## Gate-by-gate plan

### Gate 0 — Pause and preserve

**Priority:** P0  
**Estimate:** 1–2 days  
**Depends on:** nothing

**Goal**  
Stop unattended mutation and protect every current change.

**Work**

1. Disable continuous worker mutation for DashPro (and Axon-X if needed) via scheduler / employee toggles.
2. Snapshot run receipts for every recent DashPro and Axon-X employee run.
3. Inventory every changed path in `/home/edp/Projectx/product/dashpro`.
4. Map each path to a run, employee role, or “unknown”.
5. Decide keep / discard / hold for each cluster of changes.
6. Preserve both dirty trees; do not reset or force-clean without operator confirmation.

**Exit criteria**

- Scheduler mutation is paused where required.
- Every changed DashPro path has an owner and disposition.
- No worker is writing while triage is active.

**Evidence to record**

- scheduler status JSON;
- change inventory markdown;
- mapping of paths → run IDs / roles.

---

### Gate 1 — Restore a trustworthy baseline

**Priority:** P0  
**Estimate:** 2–4 days  
**Depends on:** Gate 0

**Goal**  
One known-good commit where autonomy foundations are green.

**Work**

1. Re-run autonomy-critical modules on a clean comparison or isolated DB fixture set and record pass/fail with SHA.
2. Fix any remaining scheduler-settings test isolation, roster active-run projection, retention pruning, and missing imports if they reproduce.
3. Run supported backend contract suite.
4. Run console typecheck, Vitest, and production build.
5. Run contracts / preflight gates without raising budgets.
6. Record HEAD SHA, command outputs, and pass counts.

**Exit criteria**

- Backend contract runner green at one recorded commit.
- Console typecheck / tests / build green at that same commit.
- Autonomy-critical modules green when run the supported way (not only one ad-hoc invocation).

**Evidence to record**

- `verify:contracts` result;
- Vitest summary;
- typecheck / build logs;
- commit SHA.

---

### Gate 2 — Authentication and containment

**Priority:** P0  
**Estimate:** 7–12 days  
**Depends on:** Gate 1

**Goal**  
Make powerful actions attributable and least-privilege.

**Work**

1. Authenticate every mutating control-plane API (runs, chat dispatch, terminals, fleet, vault proxy, tunnel).
2. Keep watch service internal-only with service identity / mTLS or equivalent.
3. Disable vault auto-unlock in any remotely reachable deployment.
4. Add step-up approval for Full Access and exact-effect actions.
5. Restrict scheduled Cursor flags (`--trust`, `--force`, `--approve-mcps`) to a narrower worker policy.
6. Add rate limits, CSRF / origin protection, and audit identity fields.

**Exit criteria**

- Anonymous mutation is impossible.
- Every remote action has a revocable identity.
- Workers run least-privilege by default.
- Vault unlock is explicit and audited.

**Evidence to record**

- auth middleware tests;
- denied-anonymous mutation proofs;
- vault unlock audit receipts;
- worker trust-policy tests.

---

### Gate 3 — Per-task disposable checkout

**Priority:** P0  
**Estimate:** 4–7 days  
**Depends on:** Gates 1 and 2

**Goal**  
Every continuous worker gets its own branch and worktree.

**Work**

1. Reuse safe-improvement isolation patterns for normal worker runs.
2. Create one branch + git worktree per leased task / run.
3. Pin baseline SHA before edits.
4. Forbid writes outside the disposable root.
5. Clean up failed worktrees with receipts.
6. Keep the operator live checkout read-only for continuous workers.

**Exit criteria**

- Two workers can change the same repository without sharing a working tree.
- Operator checkout remains untouched by continuous workers.
- Failed tasks leave cleanup receipts, not dirty shared folders.

**Evidence to record**

- isolation unit tests;
- concurrent-worker proof;
- before/after `git status` on the live root.

---

### Gate 4 — Durable task ledger

**Priority:** P0  
**Estimate:** 4–7 days  
**Depends on:** Gate 3

**Goal**  
Replace “pick the highest-value task” with leased, recorded work.

**Work**

1. Add task model: goal, acceptance criteria, risk, owner role, dependencies, lease, attempt budget, terminal outcome.
2. Create APIs / store for task create, lease, complete, fail, cancel.
3. Require every worker run to reference exactly one leased task.
4. Block untracked self-selected continuous work.
5. Surface task board in Mission Control / company roster.

**Exit criteria**

- Every worker run is created from one leased task.
- No continuous shift starts without a task ID.
- Attempt budgets and leases are enforced.

**Evidence to record**

- task schema + migration;
- lease contention tests;
- UI screenshot or API snapshot of a leased task.

---

### Gate 5 — Lead planner and conflict policy

**Priority:** P0  
**Estimate:** 5–8 days  
**Depends on:** Gate 4

**Goal**  
Make Dana (Lead) a real manager, not only a persona.

**Work**

1. Convert approved goals / backlog items into a dependency DAG of tasks.
2. Assign roles (frontend / backend / integrations / watcher).
3. Serialize overlapping file paths.
4. Cancel obsolete tasks when goals change.
5. Persist replan receipts.

**Exit criteria**

- One goal produces an ordered task plan.
- Overlapping edits cannot run concurrently.
- Replans are receipt-backed.

**Evidence to record**

- planner unit tests;
- conflict-serialization proof;
- sample goal → task DAG artifact.

---

### Gate 6 — Mandatory verifier contract

**Priority:** P0  
**Estimate:** 5–8 days  
**Depends on:** Gate 4

**Goal**  
Workers cannot finish without machine-checkable proof.

**Work**

1. Generate task-specific checks before execution.
2. Require lint / type / test / build / security / diff-budget checks as applicable.
3. Keep the verifier immutable to the worker.
4. Block `review_ready` / PR creation when checks fail.
5. Persist command outputs as receipts.

**Exit criteria**

- No task reaches review-ready without acceptance evidence.
- Failed checks always block publishing.
- Diff policy rejects secrets and out-of-scope paths.

**Evidence to record**

- verifier contract tests;
- fail-closed examples;
- sample acceptance receipt.

---

### Gate 7 — Independent review agent

**Priority:** P1  
**Estimate:** 3–5 days  
**Depends on:** Gate 6

**Goal**  
A second agent reviews the change; the editor is not the only judge.

**Work**

1. Run defect-first review in a separate context / role.
2. Block on actionable findings.
3. Cap repair ↔ review cycles.
4. Attach reviewer findings to the task and PR.

**Exit criteria**

- Every candidate has reviewer findings and a final pass / fail.
- Repair loops stop after the attempt budget.

**Evidence to record**

- review agent tests;
- sample finding → repair → pass trail.

---

### Gate 8 — Automated branch and PR lifecycle

**Priority:** P1  
**Estimate:** 4–7 days  
**Depends on:** Gates 3, 6, 7

**Goal**  
Successful tasks end as clean draft PRs.

**Work**

1. Create scoped commits on the task branch.
2. Push the branch.
3. Open a draft PR with evidence links.
4. Update the same PR from review / CI repairs.
5. Never merge protected branches autonomously.
6. Clean up failed worktrees and abandon branches with receipts.

**Exit criteria**

- Successful tasks leave a draft PR, not a dirty live tree.
- Failed tasks leave a cleaned-up worktree.
- Protected merges remain human-gated.

**Evidence to record**

- PR-create integration tests;
- sample draft PR URL;
- cleanup receipts.

---

### Gate 9 — Closed CI remediation loop

**Priority:** P1  
**Estimate:** 5–8 days  
**Depends on:** Gates 4 and 8

**Goal**  
CI red becomes a durable repair loop, not a chat prompt.

**Work**

1. Ingest GitHub check / workflow events for DashPro.
2. Classify the first hard-failing step.
3. Lease a repair task to the correct role.
4. Rerun the exact failing check.
5. Deduplicate alerts and escalate after attempt budget.

**Exit criteria**

- A deliberately broken test is detected, repaired on the task branch, rerun, and reflected on the PR without a new human prompt.

**Evidence to record**

- webhook handler tests;
- broken-test drill log;
- attempt-budget escalation proof.

---

### Gate 10 — Durable execution and fair scheduling

**Priority:** P1  
**Estimate:** 5–8 days  
**Depends on:** Gate 4

**Goal**  
Restarts and capacity limits no longer destroy progress or starve DashPro.

**Work**

1. Persist task leases and checkpoints.
2. Add per-workspace quotas and weighted fairness.
3. Resume safe tasks after control-plane restart.
4. Enforce token / cost / time budgets.
5. Keep usage-limit suppression, but with recovery and operator notice.

**Exit criteria**

- Restart drills recover without duplicate work.
- One workspace cannot occupy all worker slots.
- Usage exhaustion is visible and recoverable.

**Evidence to record**

- restart recovery drill;
- fairness simulation / test;
- budget enforcement tests.

---

### Gate 11 — Staging deploy and rollback

**Priority:** P1  
**Estimate:** 7–12 days  
**Depends on:** Gates 2, 8, 9, 10

**Goal**  
Prove the running app, not only the diff.

**Work**

1. Provision isolated staging for DashPro (and later Axon-X mobile).
2. Deploy immutable artifacts.
3. Run smoke / health checks.
4. Canary a small slice of traffic or synthetic checks.
5. Auto-rollback on failure.
6. Keep production promotion approval-gated.

**Exit criteria**

- A bad candidate rolls back automatically.
- Production remains approval-gated.
- Deployment receipts are retained.

**Evidence to record**

- staging deploy runbook;
- rollback drill;
- health-check receipts.

---

### Gate 12 — DashPro autonomy canary

**Priority:** P1  
**Estimate:** 2–3 weeks elapsed  
**Depends on:** Gates 5–11

**Goal**  
Prove the architecture with 20 real but bounded tasks.

**Task mix**

- UI bug;
- API bug;
- CI repair;
- dependency / config fix;
- ambiguous / failing cases;
- no-op / already-fixed cases.

**Success bar**

- ≥ 90% task completion;
- 0 live-tree corruption;
- 0 unauthorized effects;
- bounded cost;
- no unresolved duplicate execution;
- human interventions counted and declining.

**Evidence to record**

- canary scorecard;
- cost / intervention chart;
- incident list (if any).

---

### Gate 13 — Mobile web control plane (PWA first)

**Priority:** P2  
**Estimate:** 2–4 weeks  
**Depends on:** Gates 2, 10, 12

**Goal**  
A registered phone can supervise and approve exact actions safely.

**Work**

1. Package installable PWA from the existing `/mobile` shell.
2. Add authenticated push deep-links.
3. Ship run / approval / inbox views.
4. Add reconnect semantics and device revocation.
5. Do **not** claim background listening.
6. Defer native app until PWA proves the control model.

**First mobile release must support**

1. read fleet health;
2. read active-run evidence;
3. receive high-priority alerts;
4. stop a run;
5. approve or reject one exact action;
6. revoke a lost device.

**Exit criteria**

- A registered phone can inspect evidence, stop a run, and approve an exact effect.
- Anonymous phones cannot mutate anything.

**Evidence to record**

- PWA install proof;
- device enrollment / revocation tests;
- mobile approval drill.

---

### Gate 14 — Bounded production autonomy

**Priority:** P2  
**Estimate:** 2–4 weeks elapsed  
**Depends on:** Gates 11–13

**Goal**  
Allow only reversible, pre-approved production classes.

**Allowed later (examples)**

- restart a known healthy service;
- redeploy a previously approved artifact to staging;
- open a draft PR;
- rerun a failed CI job.

**Forever human-gated**

- production secrets;
- approval-policy changes;
- destructive data operations;
- force-push;
- protected-branch merge;
- Play / App Store promotion;
- irreversible migrations;
- expansion of the system’s own authority.

**Exit criteria**

- Production canary passes rollback drills.
- Authority can be globally revoked in one action.
- Incident review board signs the policy.

---

## Workstream map

| Workstream | Owns gates | Primary owners (roles) |
| --- | --- | --- |
| Stabilize & evidence | 0–1 | Lead + Integrations |
| Security containment | 2 | Backend + Integrations |
| Isolation fabric | 3 | Backend |
| Tasking & planning | 4–5 | Lead + Backend |
| Quality & review | 6–7 | Backend + Watcher |
| Publish & CI | 8–9 | Integrations + Backend |
| Reliability | 10 | Backend + Watcher |
| Release proof | 11–12 | Lead + Integrations |
| Mobile remote | 13–14 | Frontend + Integrations + Lead |

---

## Definition of done for “workspace autonomy”

A **bound workspace** (any project-path workspace, not only DashPro) is
autonomous enough only when all of the following are true for that workspace:

1. Continuous workers never write the live operator checkout.
2. Every run is tied to a leased task with acceptance checks.
3. Lead (or equivalent planner) can turn one approved goal into a conflict-safe task plan.
4. Draft PRs are the normal delivery unit.
5. CI failures create repair tasks automatically, with attempt budgets.
6. Staging rollback works without a human present.
7. A bounded canary (for example 20 tasks) meets the success bar for that workspace.
8. Merge to protected branches, store promotion, secrets, and destructive ops remain human-gated.

### DashPro proving-ground note

DashPro is the first workspace used to prove the loop above. Passing the
DashPro canary unlocks the pattern; it does **not** automatically declare every
other bound workspace done until the same controls are enabled and measured
there.

---

## Definition of done for “Axon-X mobile control plane”

Mobile autonomy / control is **done** only when:

1. Auth and device enrollment are mandatory.
2. PWA is installable and usable on a phone.
3. Push alerts deep-link to the exact run or approval.
4. A phone can stop work and approve exact effects.
5. A lost phone can be revoked immediately.
6. No background-listening claim is made.
7. Native packaging is an optional later product decision, not a blocker.

---

## Weekly operating cadence

| Cadence | Action |
| --- | --- |
| Daily | Check debt gate, scheduler status, usage limits, failed runs |
| End of each gate | Write exit evidence into this plan’s evidence log |
| Weekly | Operator review: keep / slip / cut scope |
| After Gate 12 | Freeze architecture; only harden and measure |
| After Gate 14 | Authority review and rollback drill |

---

## Evidence log

Gate exit receipts are appended in [`docs/ops/agent-reports/AUTONOMY-EVIDENCE-LOG.md`](./ops/agent-reports/AUTONOMY-EVIDENCE-LOG.md) (kept out of this file to stay under the markdown hard limit).

---

## Immediate next actions (start now)

1. Confirm Fast Gate green on the pinned commit after evidence-log extraction.
2. **Start Gate 3** — per-task disposable checkout / worktrees (scheduler stays off until ready).
3. **Do not** re-enable continuous live-checkout editing.
4. **Do not** build mobile mutation features until Gate 2 residuals (CSRF/rate-limit + forced token mode on remote) are closed.
5. On any remote deploy: set `AXON_WATCH_AUTH_MODE=local_token`, operator token, and `AXON_WATCH_INTERNAL_SERVICE_TOKEN`.

---

## Related documents

- Assessment: `docs/AXON-X-AUTONOMY-READINESS.md`
- Evidence log: `docs/ops/agent-reports/AUTONOMY-EVIDENCE-LOG.md`
- Interactive canvas: workspace canvases `axon-x-autonomy-readiness.canvas.tsx`
- Self-improvement contract: `docs/SELF_IMPROVEMENT_CONTRACT.md`
- DashPro CI playbook: `docs/planning/DASHPRO_CI_AGENT_PLAYBOOK.md`
- Child project binding: `docs/CHILD_PROJECT_WORKSPACE.md`
- Gate 0 evidence: `docs/ops/agent-reports/gate0-pause-preserve-2026-07-21.md`
- Gate 1 evidence: `docs/ops/agent-reports/gate1-trustworthy-baseline-2026-07-21.md`
- Gate 2 evidence: `docs/ops/agent-reports/gate2-auth-containment-2026-07-21.md`
