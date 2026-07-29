# Mission Control AUTONOMOUS — live monitoring notes

**When:** 2026-07-29 ~23:27 SAST
**Observer:** agent (read-only monitor of live control-plane)
**Mode observed:** `autonomy_mode=full`, `effective_autonomy=true`, scheduler effective, **3** employee shifts executing
**Last scan:** 2026-07-29T21:27:35Z · 6 workspaces · dispatched 0 / escalated 0 / skipped 54
**Pending decisions:** 4 (DashPro×2, axon-watch×1, edudashpro_school×1)

This is an observation log, not a claim that AUTONOMOUS is production-ready.

---

## Live snapshot (verified)

| Signal | Observed |
| --- | --- |
| Control-plane health | ok |
| Autonomy status | Full + effective |
| Scheduler | enabled, not env-blocked, `executing_count=3` |
| Open attend/assigned on `workspace_axon_watch` | **37** of 50 listed tasks |
| Of those | **17 email**, **13 handoff**, **7 failed_shift** |
| Pending “Needs you” | PostHog critical, Sentry critical, usage-limit blocker, Cloudflare tunnel handoff |
| Active runs | watcher×1 axon-watch, watcher×2 dashpro |

---

## Hardening (safety / fail-closed)

### H1 — Substring `token` false-positives as “dangerous”
- **Live:** Cloudflare tunnel handoff titled “tunnel **token** missing” escalated with `reason=dangerous_marker`.
- **Why wrong:** Missing connector auth is not a secrets-mutation request; it should be a bounded integrations/watcher inspect, or a dedicated connector-auth escalate kind — not “dangerous”.
- **Fix:** Narrow markers (`api token`, `auth token=`, `bearer`, vault secret assignment). Add allowlist phrases such as `token missing` / `auth=missing` for connector status.

### H2 — Attend tasks still have empty path bounds
- **Live:** Open email attend tasks show `allowed_paths=None`, `exclusive_paths=None`, `attempt_budget=2`.
- **Risk:** “Bounded specialist tasks” is policy text only; workers can still write broadly under a permissive project contract.
- **Fix:** Derive `allowed_paths` from signal/repo binding before create, or force inspect-only acceptance criteria until a path set exists.

### H3 — No usage-cap brake on Full autonomy
- **Live:** EduDashPro Thabo usage-limit failure correctly escalates as `operator_blocker`, but Full mode stays effective and other workspaces keep leasing.
- **Fix:** When any company hits usage/auth interrupt, optionally demote to Semi or pause continuous leases until operator clears the decision.

### H4 — Approval provenance must stay receipt-bound
- Already improved in code (`risk=approved` needs matching resolved receipt). Keep monitoring that generic `create_task(..., risk="approved")` cannot lease without `approval_receipt_id`.

### H5 — Secret redaction is pattern-based, not complete
- Key-aware redaction exists for receipts; still verify UI never renders raw PostHog/Sentry payloads with tokens if monitors ever embed them.

---

## Fixes (correctness / waste)

### F1 — GitHub email noise auto-dispatches into Axon-X
- **Live:** Many `VAXON attend: Email needs follow-up: [axon-control-ops/dashpro] PR run failed…` tasks land on **`workspace_axon_watch`** watchers/integrations.
- **Why wrong:** Child-repo CI mail is not Axon-X code work; burns Cursor credits on the coach workspace; duplicates Gate 9 / child Watcher ownership.
- **Fix options (prefer first):**
  1. Classify GitHub `check-suites` / PR emails as `route_only` → create handoff to `workspace_dashpro`, do not open local attend task.
  2. Or exclude email findings from auto-dispatch unless severity ≥ critical and target workspace is bound.
  3. Cap email dispatches per tick to 0–1 with aggregation (“N DashPro CI emails”) instead of one task per message.

### F2 — Dual creators for the same failed shift
- **Live:** Same dedupe key appears as both `Lead assigned:…` and `VAXON attend:…` (e.g. Rowan `failed_shift:…:run_ef2b609034c8`).
- **Cause:** Lead check-in still assigns while attend loop also dispatches `failed_shift` findings.
- **Fix:** Single owner path — either attend loop owns Full-mode assignment, or Lead check-in owns it; the other must skip when Full is on / when open task with same dedupe exists across both prefixes.

### F3 — Transient vendor criticals never age out
- **Live:** PostHog HTTP 503 “queries busy” pending ~43m; Sentry critical pending ~50m with no auto-reprobe outcome.
- **Fix:** Distinguish `transient_upstream` vs `actionable_critical`. Re-probe before escalate; auto-resolve pending if monitor returns ok; or decay to warning after N minutes without human action.

### F4 — Dedupe skips are high, queue is still crowded
- **Live:** last scan `skipped_count=54` while 17+ open email tasks remain leaseable.
- **Fix:** Completing/cancelling superseded email tasks; coalesce subject threads; stop creating new opens when N similar open tasks already exist for the same repo.

### F5 — Dirty-tree contract ratchet failures (adjacent)
- Concurrent CLI runtime catalog/router growth exceeds hotspot budgets (`catalog.py`, `catalog_snapshot.py`, `router.py`). Blocks full `verify:contracts` until extracted/ratcheted separately from autonomy.

---

## Improvements (operator UX / product)

### I1 — Pending decisions need urgency + speech
- Four “Needs you” items sat 43–50+ minutes with no VAXON interrupt observed from this monitor pass.
- **Improve:** Spoken/attention chip for pending autonomy decisions; Mission Control badge count; deep-link Approve/Reject.

### I2 — Show exact effect + workspace on every decision card
- Card has title/detail/reason; still easy to miss that PostHog/Sentry are **DashPro** while focused workspace may be Axon-X.
- **Improve:** Always show `workspace_id` + owner role + suggested exact action before Approve.

### I3 — Credit burn dashboard while AUTONOMOUS ON
- Three concurrent watcher shifts + growing email queue = uncontrolled spend risk.
- **Improve:** Live “shifts this hour / estimated Cursor burn” under the orb; soft cap that pauses new leases.

### I4 — Resume path after Hard-kill / OFF
- OFF now uses hard-kill. Operators need an obvious **Resume Full** (with confirm) on the orb after kill, not only Settings → Agents.

### I5 — Receipt stream clarity
- Successful email dispatches look like real attend work; operators cannot tell auto-noise from intentional specialist repair.
- **Improve:** Tag stream items `email_route` / `failed_shift` / `critical_decision`; tone noise as `info`, repairs as `attention`.

### I6 — Component / E2E tests still thin
- Backend concurrency/decision tests exist; Mission Control autonomy control still lacks component tests for failed poll, hard-kill partial errors, and cross-workspace pending scoping.

---

## Suggested fix order

1. **F1** stop auto-dispatching DashPro GitHub emails into Axon-X (biggest live waste).
2. **F2** unify Lead vs attend failed_shift creation.
3. **H1** fix `token` false-positive.
4. **H2** attach path bounds or inspect-only gate.
5. **F3** transient critical aging / reprobe.
6. **I1/I3** operator urgency + spend guardrails.
7. Keep Full autonomy on only for a timed drill until F1–F2 land.

---

## Commands used

```bash
curl -sS http://127.0.0.1:8787/api/health
curl -sS http://127.0.0.1:8787/api/operator/autonomy/status
curl -sS 'http://127.0.0.1:8787/api/operator/autonomy/status?workspace_id=workspace_axon_watch'
curl -sS http://127.0.0.1:8787/api/worker-scheduler
curl -sS 'http://127.0.0.1:8787/api/workspaces/workspace_axon_watch/tasks?limit=50'
curl -sS 'http://127.0.0.1:8787/api/runs?limit=30'
```

**Confidence on these notes:** **8/10** — live API receipts inspected; not a full console UI walkthrough of Approve/Reject or Hard-kill in this pass.

---

## Remediation applied 2026-07-29 ~23:35 SAST

| Action | Result |
| --- | --- |
| Hard-kill | `autonomy_mode=semi`, scheduler off, `effective_autonomy=false`; stopped 2 shifts (1 already failed) |
| F1 code | GitHub email CI noise → policy `skip` (`email_ci_noise_no_dispatch`) |
| F2 code | Full mode zeros Lead assignment creation; Lead open-task scan includes `VAXON attend:` |
| H1 code | Removed bare `token` marker; allowlist `token missing` / `auth=missing` |
| Queue cleanup | Cancelled **24** open email attend tasks; **3** attend duplicates of Lead assigned; rejected false-positive tunnel decision |
| Tests | `tests.test_autonomous_attention_policy` + `tests.test_autonomous_attention_loop` — 26 OK |

**Note:** control-plane uvicorn (no `--reload`) must be restarted once for F1/F2/H1 to apply on the next Full ON. Until then, keep Semi.
