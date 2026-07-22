# Axon-X autonomy evidence log

Append one block per completed gate. Source of truth for gate exit receipts lives in `docs/ops/agent-reports/`.

Template:

```text
### Gate N — YYYY-MM-DD
- owner:
- commit:
- commands run:
- pass/fail:
- exit criteria met: yes/no
- residual risks:
- next gate unlocked:
```

### Gate 0 — 2026-07-21
- owner: operator + agent
- commit: evidence captured against live tree; later pinned in `ad69aaf` (see `docs/ops/agent-reports/gate0-pause-preserve-2026-07-21.md`)
- commands run: `GET /api/worker-scheduler`; DashPro + axon-watch dirty inventory
- pass/fail: pass
- exit criteria met: yes (at capture)
- residual risks: DashPro OTA/affiliation KEEP cluster; Axon-X large mixed dirty tree preserved; OTA run `run_a3a0e0ab2e63` later failed (do not treat as still executing)
- next gate unlocked: Gate 1

### Gate 1 — 2026-07-21
- owner: agent
- commit: local command-green on dirty tree atop `9c86389`; first push pin `ad69aaf` (see `docs/ops/agent-reports/gate1-trustworthy-baseline-2026-07-21.md`)
- commands run: `npm run verify:contracts`; `npm run verify:console-web`
- pass/fail: pass locally before evidence-log append; Fast Gate on `ad69aaf` initially failed file-size hard limit on master plan (fixed by extracting this log)
- exit criteria met: yes for local command suite; CI confirmation follows fix commit
- residual risks: commit `ad69aaf` mixes Gates 0–2 with desktop/host/UI WIP
- next gate unlocked: Gate 2 finish / Gate 3 prep

### Gate 2 — 2026-07-21 (thin slice)
- owner: agent
- commit: included in `ad69aaf`; report `docs/ops/agent-reports/gate2-auth-containment-2026-07-21.md`
- commands run: `tests.test_gate2_auth_containment` (11 OK); included in `verify:contracts`
- pass/fail: pass for thin slice
- exit criteria met: partial — local_token + internal watch token + vault remote refuse + worker trust policy; **not** full CSRF/rate-limit/step-up
- residual risks: default auth mode still `placeholder`; must set tokens for non-loopback; rate limit/CSRF/step-up outstanding
- next gate unlocked: Gate 3 (per-task worktrees) — keep scheduler off until worktrees land

### Gate 3 — 2026-07-22
- owner: agent
- commit: `11e3bce` (named `worker/<run_id>` worktree + path forbid + concurrent proof); report `docs/ops/agent-reports/gate3-worker-isolation-2026-07-22.md`
- commands run: `python -m unittest tests.test_gate3_worker_isolation` (5 OK); `PYTHONPATH=services/control-plane python -m unittest tests.test_safe_improvement` (8 OK)
- pass/fail: pass
- exit criteria met: yes — two isolations without shared tree; live-root `git status` unchanged; cleanup deletes worktree + worker branch with receipts; path escape refused
- residual risks: path forbid is resolve-time only (not full FS sandbox); scheduler still intentionally off; Gate 2 CSRF/rate-limit/step-up still open
- next gate unlocked: Gate 4 (durable task ledger) — keep scheduler off until leases exist

### Gate 2 residuals — 2026-07-22
- owner: agent
- commit: (pin after commit) report `docs/ops/agent-reports/gate2-residuals-2026-07-22.md`
- commands run: `tests.test_gate2_auth_containment` (17 OK); `npm run verify:contracts`; `npm run verify:console-web`
- pass/fail: pass for residual thin slice (forced remote local_token, rate limit, step-up headers, origin guard retained)
- exit criteria met: yes for master-plan “CSRF/rate-limit + forced token mode on remote” before mobile mutation; mTLS still open
- residual risks: in-process rate limiter only; step-up is header confirm not OIDC; default local auth still placeholder on loopback
- next gate unlocked: Gate 4 (durable task ledger) — scheduler still off
