# Gate 2 — Authentication & containment evidence

**Date:** 2026-07-21  
**Plan:** `docs/AXON-X-AUTONOMY-MASTER-PLAN.md` Gate 2  
**Baseline HEAD (committed):** `9c86389` + uncommitted Gate 2 work  
**Depends on:** Gate 0 pause still in force; Gate 1 contracts/console green on working tree

---

## What shipped in this slice

### Control-plane mutating auth

- `services/control-plane/app/auth/` — `MutatingAuthMiddleware`, settings, identity, audit, desktop session
- Wired in `services/control-plane/app/main.py`
- Modes: `off` / `placeholder` (local bootstrap) vs `local_token` (Bearer / `X-Axon-Operator-Token`)
- Loopback bypass controlled by `AXON_WATCH_AUTH_ALLOW_LOOPBACK`
- Proofs in `tests/test_gate2_auth_containment.py`:
  - anonymous mutation → **401** when `local_token` + loopback bypass off
  - bearer token allows mutation
  - `/api/health` remains public

### Watch service identity (CP → watch)

- `services/axon-watch/app/internal_auth.py` — `InternalServiceTokenMiddleware`
- When `AXON_WATCH_INTERNAL_SERVICE_TOKEN` is set, mutating `/internal/watch/*` requires `X-Axon-Internal-Token`
- Health/readiness exempt
- CP `watch_client` / `watch_http.py` attach the header when configured
- Documented in `.env.example`
- Proofs: denied without token; allowed with token; health public

### Vault auto-unlock containment

- CP refuses enable when remotely reachable (403 + audit)
- Watch `enable_auto_unlock` / `attempt_auto_unlock` refuse when remotely reachable

### Worker Cursor least-privilege

- `build_cursor_agent_command(..., trust_policy="worker")` omits `--force` / `--approve-mcps`
- Operator policy retains them when research available
- Continuous workers dispatch with `cursor_trust_policy="worker"`

---

## Test proof

```text
./scripts/dev/python.sh -m unittest -q tests.test_gate2_auth_containment
Ran 11 tests … OK
```

Included in `npm run verify:contracts` via `scripts/verify/run_contract_unit_tests.sh`.

---

## Gate 2 exit checklist (honest)

| Criterion | Status |
| --- | --- |
| Anonymous mutation impossible | **Conditional** — enforced when `AXON_WATCH_AUTH_MODE=local_token` (and loopback bypass off). Default `.env.example` remains `placeholder` for local bootstrap. |
| Every remote action has revocable identity | **Partial** — operator token + optional internal service token; no full OIDC/session revocation product yet. |
| Workers least-privilege by default | **Met** for Cursor flag policy on worker trust. |
| Vault unlock explicit + audited | **Met** for remote auto-unlock refusal + CP audit on enable attempt. |
| Rate limits / CSRF / step-up Full Access | **Partial** — same-origin Origin/Referer guard on mutating routes when remotely reachable (`app/auth/origin_guard.py`). Rate limits + step-up Full Access still residual. |
| mTLS watch exposure | **Not done** — shared secret is the thin equivalent for now. |

**Gate 2 result:** **Thin containment slice CLOSED** for unlocking Gate 3 engineering.  
**Not** a claim that production remote autonomy is fully auth-hardened.

---

## Residual risks before remote / mobile mutation

1. Leave `AXON_WATCH_AUTH_MODE=local_token` + strong `AXON_WATCH_OPERATOR_TOKEN` on any non-loopback deploy.
2. Set matching `AXON_WATCH_INTERNAL_SERVICE_TOKEN` on CP and watch.
3. Keep scheduler `effective_enabled: false` until Gate 3 worktrees exist.
4. Add CSRF/origin checks + rate limits before exposing mutating APIs beyond loopback.
5. Step-up approval for Full Access / exact-effect actions still outstanding.

---

## Scheduler pause reconfirmed (Gate 0 still holds)

`GET /api/worker-scheduler` @ 2026-07-21T14:46:47Z:

- `scheduler_enabled: false`
- `effective_enabled: false`
- `executing_count: 0`
