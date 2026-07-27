# Auto-loop status & credits budget (operator brief)

**Read this first when someone asks: “Are we autonomous yet?”**  
**Last updated:** 2026-07-25

---

## 1. Short answer

**No — Axon-X is not yet on a closed unattended auto-loop.**

What you have today is a **strong supervised company**: named employees, leased
tasks, worktree isolation, Gate 6 acceptance, draft-PR delivery, Gate 9 CI
repair, and (new) proactive file-size patrol *plumbing*. What you do **not**
have is “Dana hands off, everyone runs overnight, and Mission Control only
shows green in the morning” without operator nudges.

If Mission Control still shows any of these, you are in **supervised mode**:

| UI signal | Meaning |
| --- | --- |
| **RETRY SHIFT** | A worker run failed; a human (or Lead) must restart it |
| **Shall I dig in?** / Yes–Not now | VAXON needs operator confirmation |
| **Last shift failed: Critical Review Clause missing…** | Shift ended without a valid `Confidence: N/10` receipt |
| **0 active runs** + many open signals | Work is queued for review, not continuously draining |
| Typing “handoff the tasks” into Lead chat | Fan-out / lease pickup is not fully self-driving yet |

That matches the DashPro screen on 2026-07-25: Marco failed Critical Review,
Expo called out as down, Lead recommended next steps, and the operator had to
type the handoff.

---

## 2. What *is* automatic today

| Loop piece | Status | Notes |
| --- | --- | --- |
| Create / lease durable tasks (Gate 4) | **Ready** | Continuous workers require a leased task |
| Lead plan → fan-out → specialist tasks (Gate 5) | **Ready** | Persist + ready runs; still often needs scheduler or Retry |
| Disposable worker worktrees (Gate 3) | **Ready** | Live checkout edits forbidden for continuous workers |
| Gate 6 verifier / acceptance evidence | **Ready** | Failed checks block completion/publish path |
| Draft PR delivery (no force-push) | **Ready** | Company pattern for publish |
| Gate 9 CI remediation (webhook → repair task) | **Proven for Axon-X** | Reactive self-heal when Fast Gate goes red |
| Per-task `allowed_paths` guardrails | **Ready (new)** | Hard scope for writes/publish + prompt anchors |
| File-size patrol work source | **Plumbing ready** | Scheduler can enqueue bounded hygiene tasks when enabled |
| Continuous worker scheduler | **Off by default** | Intentional — turn on only for watched drills |
| Unattended overnight multi-project loop | **Not ready** | Still needs human dig-in / retry / Critical Review hygiene |
| Staging / production deploy autonomy | **Not ready** | Remains human-gated |

Check the scheduler before assuming anything is looping:

```bash
curl -sS http://127.0.0.1:8787/api/worker-scheduler \
  | jq '{scheduler_enabled, effective_enabled, executing_count}'
```

Expect `effective_enabled: false` on the daily-driver host unless you
deliberately enabled it for a drill.

---

## 3. What “auto-loop” must mean before we claim it

A workspace is on a real auto-loop only when **all** of these are true without
operator chat prompts:

1. Open work is created from signals / Lead / hygiene sources (not only typed handoffs).
2. The scheduler claims leased tasks for the right roles on its own.
3. Shifts reliably end with Critical Review + `Confidence: N/10`.
4. Failed shifts reopen or escalate with a clear receipt (not a silent zombie lease).
5. Passing work becomes a **draft PR**; CI red creates a **bounded repair** (Gate 9).
6. Out-of-scope drift is blocked (allowed paths + scope guard).
7. You can leave the machine for hours and return to draft PRs / green repair heads —
   not a wall of RETRY SHIFT and dig-in prompts.

Until then: call it **bounded supervised autonomy**, not auto-loop.

---

## 4. Credits & subscription budget (Cursor + friends)

Axon continuous workers burn **Cursor Agent / CLI usage** (subscription pool or
API key). Pricing moves; treat numbers below as **2026 order-of-magnitude**
planning, and verify in the Cursor dashboard.

### Cursor plans (individual / small team)

| Plan | Rough monthly price | Included model usage (guide) | Fit for Axon-X |
| --- | ---: | --- | --- |
| **Pro** | ~$20 | ~$20 API-equivalent | Operator + occasional IDE agent; **not** multi-project continuous |
| **Pro+** | ~$60 | ~$70 | 1 proving workspace, light scheduler drills, prefer **Auto** |
| **Ultra** | ~$200 | ~$400 | Serious continuous agents on 1–2 busy workspaces |
| **Teams** | ~$40/user | Per-seat allowance | Shared billing / analytics; still need Ultra-class usage for many agents |

Sources to re-check: [Cursor pricing help](https://cursor.com/help/account-and-billing/pricing),
[Models & pricing](https://cursor.com/docs/models-and-pricing).

**Rule of thumb:** prefer **Auto** / cheaper router models for patrol and routine
shifts; save frontier models for Lead synthesis and hard repairs. Frontier /
MAX-style sessions can empty even Ultra in days.

### How much autonomy burns (planning ranges)

Assume one “shift” ≈ one continuous worker run with tools (often many model
turns). Costs vary wildly by model and repo size.

| Operating mode | Shifts / day (all projects) | Suggested Cursor tier | Monthly Cursor budget to plan |
| --- | ---: | --- | ---: |
| Supervised operator (today’s default) | 2–8 manual / Retry | Pro or Pro+ | **$20–$100** |
| Bounded auto-loop drill (1 workspace, scheduler on, watched) | 10–25 | Pro+ → Ultra | **$100–$250** |
| Multi-project autonomous (3–6 workspaces, CI repair + patrol) | 30–80 | Ultra + on-demand, or Teams + pooled | **$250–$800+** |
| Aggressive 24/7 multi-agent (not recommended yet) | 100+ | Ultra + hard spend caps | **$800–$2,000+** |

These are **planning envelopes**, not invoices. Track real burn for one week of
drills before buying more seats.

### Other credits you will also need

| Surface | Why it matters | Rough planning note |
| --- | --- | --- |
| **GitHub Actions** | Fast Gate / child CI on every draft PR | Private repos: minutes; keep repair PRs small |
| **Supabase / cloud DBs** | DashPro storage already ~60% of 1 GB in the UI snapshot | Budget storage + egress; don’t let agents spam uploads |
| **Sentry / PostHog** | Watch signals drive “dig in” | Event volume rises with more projects |
| **Azure TTS / voice** | Talk / briefing | Small vs Cursor; still meter it |
| **Host RAM / OOM** | Control-plane can die (exit 137) under concurrent agents | Cap `max_active` (default 2); more projects ≠ more concurrent agents |

### Practical recommendation (multi-project)

1. **Stay supervised** until Critical Review failures and RETRY SHIFT noise are rare.
2. Run **one proving workspace** (DashPro or Axon-X) with scheduler on for short drills.
3. Budget **Ultra (~$200–400/mo usage)** before enabling continuous workers on 3+ projects.
4. Set a Cursor **spend limit** so on-demand cannot surprise you.
5. Keep Axon `max_active_executing` at **2** (or 1) — credits and RAM both explode with concurrency.

---

## 5. Operator checklist (today)

1. Confirm control-plane health: `curl -sS http://127.0.0.1:8787/api/health`
2. Confirm scheduler off unless drilling: see §2 command.
3. Clear failed Critical Review shifts (Retry or cancel stale tasks).
4. Prefer explicit tasks / Lead fan-out over free-form “go ahead and handoff” chat.
5. After any push: `./scripts/ops/watch-fast-gate.sh`
6. Re-read this page after each autonomy gate change.

Related:

- [`autonomy-gates-and-service-identity.md`](autonomy-gates-and-service-identity.md)
- [`recent-operator-features.md`](recent-operator-features.md)
- [`docs/AXON-X-AUTONOMY-MASTER-PLAN.md`](../AXON-X-AUTONOMY-MASTER-PLAN.md)
- [`docs/AXON-X-AUTONOMY-READINESS.md`](../AXON-X-AUTONOMY-READINESS.md)
