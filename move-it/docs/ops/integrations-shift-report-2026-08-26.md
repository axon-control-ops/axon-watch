# Integrations shift report — MoveIT service bridge scaffold

| Field | Value |
|---|---|
| Retry run (this turn) | `run_b5d82a6fc8a3` |
| Failed run retried | `run_507751a44a89` |
| Failed task | `task-e77013a67795452b` |
| Prior retry | `run_40c26f141654` (Gate 6 / delivery) |
| Role | Sol (Integrations) |
| Date | 2026-08-26 |

## What failed last time

Run `run_507751a44a89` passed completion-gate preflight and verification (2/3 terminal jobs), then publish failed:

> Workspace delivery blocked: workspace delivery is not configured for MoveIT, so 5 changed path(s) cannot be published

Blocked paths from gate receipt:

1. `docs/ops/MoveIt-MVP-UI-UX-Design-Spec.md`
2. `docs/ops/integrations-shift-report-2026-08-26.md`
3. `docs/ops/lead-handoff-node-manifests-2026-08-26.md`
4. `docs/ops/watcher-health-receipt-2026-08-26.json`
5. `docs/ops/watcher-shift-report-2026-08-26.md`

Isolation checkout was preserved at `/tmp/axon-si-run_507751a4-sum7fcw5/checkout` (may be cleaned up now). Integration scaffold artifacts (`config/env.example`, tests, verify script) were already on disk from prior shift `run_40c26f141654`.

## What this retry changed

| Path | Purpose |
|---|---|
| `config/env.example` | Operator env template — all 10 keys from `GET .../service-connection` |
| `tests/integrations.env.example.test.js` | Contract test — keys present, no secret-like values |
| `scripts/integrations/verify-service-bridge.sh` | Repeatable live verify for gh / sentry-cli / supabase |
| `package.json` | `npm test` runs all `tests/*.test.js` |

**Note:** Project root `.env.example` is read-only in this worker scope (EROFS). Template lives at `config/env.example`; copy to `.env` at root when materializing operator secrets.

## Verified this turn (retry `run_b5d82a6fc8a3`)

| Check | Receipt |
|---|---|
| Service connection | `GET .../service-connection` → `configured=true`, `ready=true`, `services_resolved` github/sentry/supabase all true |
| Workspace delivery | `GET .../delivery` → **HTTP 200**, `configured=true`, `push_policy=draft_pr`, repo `axon-control-ops/move-it` — **unblocked since failed run** |
| npm test (full) | `agent-job-9eb16fb3daa1` exit 0 — 5 pass / 0 fail |
| npm test (integrations) | `agent-job-b7065939a80f` exit 0 — env template contract test pass |
| Env keys covered | 10 keys match API `env_keys` list |
| Vault partial | GH_TOKEN, SENTRY_AUTH_TOKEN, SUPABASE_ACCESS_TOKEN from vault; URL/org/project keys still missing |
| Secret scan (test) | no `sk_`, `ghp_`, or JWT-like values in template |
| Live verify | `agent-job-194e24f01560` exit 1 — gh + supabase PASS; sentry-cli FAIL (missing SENTRY_ORG/PROJECT in vault) |

## Blockers / Lead next

1. **Delivery config fixed** — `GET .../delivery` now returns 200; the `run_507751a44a89` blocker is cleared.
2. **New publish gate** — pipeline shows `private_company_material` on `output/delivery-probe-2026-08-26.txt` (from `run_d8321fc42916`). Remove or relocate that file before the next continuous-worker publish; it was never staged or pushed.
3. **Sentry live verify** — still fails until `SENTRY_ORG` / `SENTRY_PROJECT` are in vault or operator `.env`.
4. Operator `.env` still absent — optional while vault supplies partial keys; Sir King can `cp config/env.example .env` and fill missing URL/org/project keys.
