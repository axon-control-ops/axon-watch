# Auto Ask Autopilot — 2026-08-10

## Goal

Prevent Full Auto continuous workers from parking leased tasks on safe,
reversible ask cards while still preserving hard stops for human decisions.

## Behavior

When a continuous worker emits an Axon `:::ask` card, the control plane now
checks whether Full Auto is enabled and whether the options are safe engineering
continuations. If so, it records an `auto_ask_resolution` receipt, selects the
least-risk progress option, fails/reopens the no-change worker attempt with that
selected answer in the failure detail, and lets the scheduler start the next
shift with the prior answer visible in the worker prompt.

Auto may continue on choices such as:

- continuing diagnosis;
- clearing local cache or hard refresh;
- hardening a route or import boundary;
- running targeted verification;
- taking the smallest reversible implementation step.

Auto must not continue on choices involving:

- destructive data changes;
- credentials, tokens, secrets, or passwords;
- billing, payments, or spending;
- production deploy/release/merge/push;
- irreversible product behavior or customer/account decisions.

## Evidence files

| Concern | File |
| --- | --- |
| Ask-card parser and safety policy | `services/control-plane/app/workspace_agents/ask_autopilot.py` |
| Continuous-worker integration | `services/control-plane/app/workspace_agents/worker_dispatch.py` |
| Worker prompt instruction | `services/control-plane/app/workspace_agents/worker_prompt.py` |
| Progress/heartbeat extraction | `services/control-plane/app/workspace_agents/worker_dispatch_progress.py` |
| Policy/unit tests | `tests/test_worker_ask_autopilot.py` |
| Dispatch regression test | `tests/test_worker_ask_autopilot_dispatch.py` |

## Verification

- `./scripts/dev/python.sh -m unittest tests.test_worker_ask_autopilot tests.test_worker_ask_autopilot_dispatch tests.test_workspace_agent_scheduler tests.test_run_stale_reconcile -v`
- `npm run verify:file-sizes`
