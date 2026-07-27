# Gate 9 — CI remediation (unaware-operator loop)

**Updated:** 2026-07-24

When **Axon-X Fast Gate** goes red, control-plane can ingest the GitHub
`workflow_run` event, raise an inbox signal, lease a repair task to Rowan
(watcher), one-shot dispatch a worker, and report the outcome — without you
watching the Actions tab.

## What is wired (v1)

| Step | Behavior |
|------|----------|
| Ingest | `POST /api/webhooks/github/workflow-run` (HMAC `X-Hub-Signature-256`) |
| Config | [`config/ci-remediation.json`](../../config/ci-remediation.json) — Axon-X Fast Gate and all six active DashPro workflows enabled |
| Dedup | One open repair per `(repo, workflow, branch, head_sha)` |
| Signal | Inbox item source `ci_remediation` merged in control-plane inbox projection |
| Lease | Task ledger goal starts with `CI repair:` · owner_role `watcher` |
| Dispatch | Background `dispatch_continuous_worker_run` when `dispatch_on_ingest` is true |
| Report | Worker posts `POST /api/ci-remediation/report-outcome` → signal + spoken line |

**Still human-gated:** merge to `dev`/`master`, force-push, secrets.

## GitHub webhook setup

1. Set `AXON_WATCH_GITHUB_WEBHOOK_SECRET` (or `GITHUB_WEBHOOK_SECRET`) on the control-plane host.
2. In GitHub → repo **Settings → Webhooks**:
   - Payload URL: `https://<control-plane>/api/webhooks/github/workflow-run`
   - Content type: `application/json`
   - Secret: same as the env var
   - Events: **Workflow runs**
3. Confirm delivery with a red Fast Gate push; inbox should show
   `Axon-X Fast Gate failed on <branch>`.

## Local poll fallback (when public tunnel/DNS is down)

GitHub webhook deliveries fail with `connection_error` if
`axon.edudashpro.org.za` does not resolve or the tunnel is degraded.
Config alone cannot auto-fix CI in that state — Rowan never sees the event.

Use the local poller (HMAC to control-plane on localhost):

```bash
CONTROL_PLANE_URL=http://127.0.0.1:8787 \
  ./scripts/ops/poll-fast-gate-remediation.sh
```

Always-on timer (user systemd):

```bash
mkdir -p ~/.config/systemd/user
cp scripts/ops/systemd/axon-fast-gate-remediation-poll.{service,timer} \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now axon-fast-gate-remediation-poll.timer
```

Public webhook remains preferred; the timer only covers tunnel/DNS outages.

## Operator surfaces

- **Attention / inbox** — CI failure and repair/blocked updates
- **Task board** — leased `CI repair:` task for Rowan (escalate role Quinn)
- **Voice** — report-outcome returns a `spoken` line; ask-shaped dig-in on budget exhaustion

## Enabled workspaces

- Axon-X: `Axon-X Fast Gate`
- DashPro: `CI`, `Android CI/CD Pipeline`, `Database SQL Linting`,
  `Docs Policy Enforcement`, `Security Scan`, and `Voice Benchmark Nightly`

For another workspace, add an enabled binding in `config/ci-remediation.json`
with the correct repository and workflow names. No new core code is required.

## Local verify

```bash
./scripts/dev/python.sh -m unittest tests.test_ci_remediation -v
```

Manual drill: push a deliberate Fast Gate ratchet overshoot on a throwaway
branch, confirm webhook → signal → leased task → repair draft PR → green head,
then append evidence under `docs/ops/agent-reports/AUTONOMY-EVIDENCE-LOG.md`.
