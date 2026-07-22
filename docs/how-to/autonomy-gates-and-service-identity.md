# Autonomy gates & service identity (operator directives)

**Do this in order. Do not skip ahead.**

This page is the short, directive companion to
[`docs/AXON-X-AUTONOMY-MASTER-PLAN.md`](../AXON-X-AUTONOMY-MASTER-PLAN.md).
It tells you **what to turn on**, **what to leave off**, and **how to prove it**.

**Last updated:** 2026-07-22

---

## 1. Current gate status (what “done” means)

| Gate | Status | You must |
| --- | --- | --- |
| **0–1** | Closed | Keep a known-good commit; do not mix unrelated dirty trees into autonomy PRs |
| **2 thin + residuals** | Closed | Use `local_token` on any non-loopback surface; set operator + internal tokens |
| **3** | Closed | Continuous workers use disposable `worker/<run_id>` worktrees only |
| **4** | Closed | Continuous workers only run from a **leased task**; scheduler stays **off** until you intentionally enable it |
| **5** | In progress | Persist + ready fan-out runs land; do **not** enable continuous scheduler / Lane B auto-dispatch yet |

**Scheduler rule (non-negotiable for now):** keep continuous workers
`effective_enabled: false` unless you are deliberately testing Gate 4 with a
bounded task board and you are watching the machine.

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

## 3. Watch service identity (token + mTLS)

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

### mTLS (required for production remote)

Axon-X supports proxy-verified client certificates **plus** the shared token.

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

## 4. Control-plane operator auth (reminder)

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

## 5. Verify before you claim a gate closed

```bash
npm run verify:contracts
npm run verify:console-web
# then push and confirm Axon-X Fast Gate is green on GitHub
```

Evidence lives under `docs/ops/agent-reports/` and the roll-up log
`docs/ops/agent-reports/AUTONOMY-EVIDENCE-LOG.md`.

---

## 6. What to build next

1. Gate 5 — Lead planner / conflict policy / fan-out  
2. Keep scheduler off until leases + Lead assignment are routine  
3. Do not expand mobile mutation until this page’s remote auth + mTLS steps are live on that host
