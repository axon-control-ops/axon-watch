# Gate 2 residuals — CSRF / rate-limit / step-up / remote local_token

**Date:** 2026-07-22  
**Plan:** `docs/AXON-X-AUTONOMY-MASTER-PLAN.md` Gate 2 residuals (before Gate 4 / mobile mutation)  
**Depends on:** Gate 2 thin slice (`docs/ops/agent-reports/gate2-auth-containment-2026-07-21.md`); Gate 3 closed (`11e3bce`)

---

## What shipped

### Forced `local_token` on remote

- `auth_mode()` returns `local_token` when `is_remotely_reachable()` even if env is `placeholder`/`off`
- `allow_loopback_bypass()` is **false** whenever remotely reachable
- Install/always-on scripts remain belt-and-suspenders; runtime now enforces the same rule

### Rate limits

- `app/auth/rate_limit.py` — sliding 60s window per identity+client on mutating routes
- Default `AXON_WATCH_MUTATING_RATE_LIMIT_PER_MINUTE=120` (`0` disables)
- Wired in `MutatingAuthMiddleware` → HTTP **429**

### CSRF / origin

- Existing `origin_guard.py` same-origin check retained (remote + mismatched Origin/Referer → 403)

### Step-up Full Access / exact-effect

- `app/auth/step_up.py` — when remotely reachable, require `X-Axon-Step-Up: full-access` for Full Access chat posts and `X-Axon-Step-Up: exact-effect` for safe-improvement approve/execute
- Console `postChatMessage` sends the Full Access step-up header when `execution_access === 'full'`
- Loopback / non-remote surfaces skip step-up (consent UI + body flag remain enough locally)

---

## Test proof

```text
./scripts/dev/python.sh -m unittest tests.test_gate2_auth_containment -q
Ran 17 tests … OK
```

New residual cases: remote forces local_token; step-up required when remote; rate limit trips.

---

## Honest residual after this slice

| Item | Status |
| --- | --- |
| Forced token mode on remote | **Met** (runtime) |
| CSRF / origin on mutating APIs | **Met** (thin Origin/Referer guard) |
| Mutating rate limits | **Met** (in-process; not distributed) |
| Step-up Full Access / exact-effect | **Met** for remote header confirm; not a full OIDC step-up session product |
| watch mTLS | **Still open** (shared internal token remains) |
| Default local `.env` still `placeholder` | **Intentional** for loopback bootstrap |

**Result:** Gate 2 residuals called out before mobile/remote mutation are **closed** for this thin slice. Scheduler remains off. Gate 4 may proceed on local ledger work.

---

## Scheduler

No change — keep `effective_enabled: false` until Gate 4 leases exist.
