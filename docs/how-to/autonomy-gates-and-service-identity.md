# Autonomy gates & service identity (operator directives)

**Do this in order. Do not skip ahead.**

This page is the short, directive companion to
[`docs/AXON-X-AUTONOMY-MASTER-PLAN.md`](../AXON-X-AUTONOMY-MASTER-PLAN.md).
It tells you **what to turn on**, **what to leave off**, and **how to prove it**.

**Last updated:** 2026-07-25

**Are we on auto-loop?** **No.** See
[`auto-loop-and-credits.md`](auto-loop-and-credits.md) for the operator brief
and Cursor credit budgets. Plumbing for Gates 6/9 and task-scope guardrails is
in; unattended multi-project overnight loops are not.

---

## 1. Current gate status (what “done” means)

| Gate | Status | You must |
| --- | --- | --- |
| **0–1** | Closed | Keep a known-good commit; do not mix unrelated dirty trees into autonomy PRs |
| **2 thin + residuals** | Closed | Use `local_token` on any non-loopback surface; set operator + internal tokens |
| **3** | Closed | Continuous workers use disposable `worker/<run_id>` worktrees only |
| **4** | Closed | Continuous workers only run from a **leased task**; scheduler stays **off** until you intentionally enable it |
| **5** | Closed | Use Lead plan/fan-out/replan APIs; keep scheduler off unless you are watching a drill |
| **6** | Closed (thin) | Acceptance evidence / verifier must pass before completion/publish; task `allowed_paths` intersect contract scope |
| **9** | Proven (Axon-X) | Fast Gate red → CI repair task → draft PR → re-watch; supersede old repair chains; no protected merge |

**Scheduler rule (non-negotiable for daily driving):** keep continuous workers
`effective_enabled: false` unless you are deliberately drilling with a bounded
task board and you are watching the machine. Enabling the scheduler is **not**
the same as claiming a closed auto-loop — RETRY SHIFT / Critical Review failures
still need human attention.

Check:

```bash
curl -sS http://127.0.0.1:8787/api/worker-scheduler | jq '{scheduler_enabled, effective_enabled, executing_count}'
```

Expect `effective_enabled: false` on the daily-driver host.

---

## 2. Gate 4 — Task ledger (how to use it)

### What it is

Every continuous worker shift must bind to one durable task with:

- goal + acceptance criteria
- owner role
- attempt budget
- lease holder + expiry
- terminal outcome (`completed` / `failed` / `cancelled`)

Mission Control shows the board (open / leased / done / failed).

### Operator actions

1. **Create a task** (API or Mission Control task board):
   - `POST /api/workspaces/{workspace_id}/tasks`
2. **Leave the scheduler off** unless you mean to run continuous workers.
3. When a worker claims work, the control plane **leases** the task, creates a run
   with that `task_id`, and refuses dispatch without a leased task.
4. Long shifts **renew** the lease at dispatch start so mid-run expiry does not
   silently drop ownership.
5. Dependencies must be `completed` before a dependent task can lease.

### Do / Don’t

| Do | Don’t |
| --- | --- |
| Create explicit tasks before enabling continuous workers | Let workers “pick something useful” without a task ID |
| Keep attempt budgets small (default 3) | Leave infinite retries |
| Cancel obsolete open tasks when goals change | Leave stale open tasks for the wrong role |
| Verify with `tests.test_gate4_task_ledger` | Treat Gate 4 as done if only the UI exists |

Proof commands:

```bash
./scripts/dev/python.sh -m unittest tests.test_gate4_task_ledger -q
curl -sS http://127.0.0.1:8787/api/workspaces/workspace_demo/tasks | jq .
```

---

## 3. Gate 5 — Lead planner (how to use it)

### Operator actions

1. Preview a goal as an ordered DAG:
   `POST /api/workspaces/{workspace_id}/lead/plan`
2. Materialize tasks and dependency-ready specialist runs:
   `POST /api/workspaces/{workspace_id}/lead/fan-out`
3. When the goal changes, use:
   `POST /api/workspaces/{workspace_id}/lead/replan`
   — do not manually leave obsolete tasks open.
4. After all specialist tasks are terminal, call:
   `POST /api/lead/plans/{plan_id}/synthesize`

### Safety rules

- Lead assigns only company-roster specialist roles.
- Exact and parent/child path overlaps cannot lease concurrently.
- Explicit replans stop/cancel obsolete active work and persist receipts.
- “Check with all teammates” creates one leased task/run per specialist; it never
  picks one winner. It does not automatically open IDE tabs.
- Keep the continuous scheduler **off**. Gate 5 creates ready runs but does not
  authorize unattended verification.

Proof:

```bash
./scripts/dev/python.sh -m unittest \
  tests.test_lead_task_plan \
  tests.test_lead_fan_out \
  tests.test_lead_replan -q
```

---

## 4. Watch service identity (token + proxy mTLS)

Control-plane talks to watch on `/internal/watch/*`. That path must never be
anonymous on a reachable host.

### Minimum (required on remote)

Set the **same** shared token on control-plane and watch:

```bash
# ~/.config/axon-watch/deployment.env
AXON_WATCH_INTERNAL_SERVICE_TOKEN=<long random secret>
AXON_WATCH_REMOTELY_REACHABLE=1   # or a non-loopback AXON_WATCH_PUBLIC_BASE_URL
```

**Do:** generate with `openssl rand -hex 24`  
**Don’t:** leave the token empty on a tunnel / public URL  
**Don’t:** expose watch port `:8788` on the public internet

When remotely reachable, watch **refuses** mutating internal routes if the token
is missing (HTTP 503) or wrong (HTTP 401).

### Proxy mTLS capability (deployment proof required)

Axon-X supports proxy-verified client certificates **plus** the shared token.
This is not end-to-end proof by itself: the proxy must strip incoming
verification headers, verify the certificate, and be the only network path to
watch.

1. Mint certs once:

```bash
./scripts/ops/mint-watch-mtls.sh
# writes ~/.config/axon-watch/mtls/{ca,client,server}.{crt,key}
```

2. Put this in `deployment.env` (both services):

```bash
AXON_WATCH_MTLS_REQUIRED=1
AXON_WATCH_MTLS_CA_FILE=$HOME/.config/axon-watch/mtls/ca.crt
AXON_WATCH_MTLS_CLIENT_CERT=$HOME/.config/axon-watch/mtls/client.crt
AXON_WATCH_MTLS_CLIENT_KEY=$HOME/.config/axon-watch/mtls/client.key
AXON_WATCH_MTLS_ALLOWED_CN=axon-control-plane
```

3. Configure the reverse proxy in front of watch to verify the client cert and
   forward:

- `X-SSL-Client-Verify: SUCCESS`
- `X-SSL-Client-S-DN: CN=axon-control-plane`

4. Restart: `axonrestart`

**Do:** keep token **and** mTLS together  
**Don’t:** enable `AXON_WATCH_MTLS_REQUIRED=1` without proxy verify headers (every
mutating watch call will 401)  
**Don’t:** commit private keys into git

Proof:

```bash
./scripts/dev/python.sh -m unittest tests.test_gate2_auth_containment.Gate2WatchInternalTokenTests -q
```

---

## 5. Control-plane operator auth (reminder)

On any remotely reachable console:

```bash
AXON_WATCH_AUTH_MODE=local_token
AXON_WATCH_OPERATOR_TOKEN=<strong secret>
AXON_WATCH_AUTH_ALLOW_LOOPBACK=0
```

Remote surfaces **force** `local_token` even if env still says `placeholder`.
Full Access / exact-effect on remote also require step-up header
`X-Axon-Step-Up` (`full-access` or `exact-effect`).

---

## 6. Verify before you claim a gate closed

```bash
npm run verify:contracts
npm run verify:console-web
# then push and confirm Axon-X Fast Gate is green on GitHub
```

Evidence lives under `docs/ops/agent-reports/` and the roll-up log
`docs/ops/agent-reports/AUTONOMY-EVIDENCE-LOG.md`.

---

## 7. What to build next

1. Drive Critical Review + `Confidence: N/10` failure rate near zero (today’s biggest auto-loop blocker in Mission Control)
2. Keep scheduler off by default; enable only for watched single-workspace drills
3. Harden multi-workspace work sources (CI repair + file-size patrol) under credit/RAM caps
4. Do not expand mobile mutation until this page’s remote auth + mTLS steps are live on that host
5. Re-read [`auto-loop-and-credits.md`](auto-loop-and-credits.md) before buying Ultra / enabling 3+ projects
