# Lead watcher recovery receipt — 2026-08-24

Task: `task-d8855ed739d844bf`  
Plan: `lead-plan-8b5c5b57213b4fa9`  
Required failed run: `run_44cf25bba218`  
Prior watcher run: `run_1f8dd57851ab`

## Result

The watcher item is not complete. The local control plane is ready, but the watch
service is disconnected and the runtime summary is degraded. The named failed
run cannot be fetched under this shift's command policy, and GitHub CLI is not
authenticated, so neither the exact failing test, the diff-budget path/limit,
nor the current Fast Gate conclusion can be verified. No service-health or
Fast-Gate success is claimed.

No live watcher machine receipt exists in `docs/ops/agent-reports/`; the watchers
have not reported.

## Exact checks and results

| Check | Result | Evidence |
| --- | --- | --- |
| Fetch required run log | Blocked | `axon-runlog run_44cf25bba218` exited `127`: `zsh:1: command not found: axon-runlog` |
| Fetch through approved workspace helper | Blocked | `axon-agent-terminal-job --workspace workspace_axon_watch -- axon-runlog run_44cf25bba218` exited `1`: `terminal job request failed (400): {"detail":"Sandbox policy denied the action (command does not match an approved wrapper or command prefix). Use an approved wrapper."}` |
| Existing scoped receipt for required/prior run | Not found | `rg -n --hidden --glob 'docs/ops/agent-reports/**' 'run_44cf25bba218|run_1f8dd57851ab' docs/ops/agent-reports` exited `1` with no matches |
| Control-plane health | Pass | `GET http://127.0.0.1:8787/health` returned `service=control-plane`, `status=ok`, `mode=bootstrap`, boot ID `adf08dbc23e1422cbb1f9a174d79a4de` |
| Runtime summary | Degraded | Generated `2026-08-24T05:45:30Z`; `control_plane.ready=true`, uptime `1573s`; `watch.status=unavailable`, `connected=false`; degraded reason: `Connection refused on http://127.0.0.1:8788/internal/watch/readiness` |
| Signals | Observed, not a health proof | Runtime summary returned `open_count=0`, `critical_count=0`, `high_count=0` |
| Connectors | No configured coverage | Runtime summary returned `configured=0`, `ok=0`, `degraded=0`, `unavailable=0`; this does not prove connector health |
| Fast Gate | Blocked | `gh run list --workflow 'Fast Gate' --limit 1 --json databaseId,status,conclusion,headBranch,url` exited `4`: GitHub CLI requested `gh auth login` or `GH_TOKEN` |

## Lead decision and next move

The parent plan remains active and blocked. I did not reopen the completed
frontend work, change product code, push, ship, merge, or claim current service
health.

The required handoff cannot yet name a concrete failing test or diff-budget
path/limit because the authoritative run log is inaccessible. Restore an
approved read-only `axon-runlog` wrapper (or provide the run receipt) and GitHub
CLI authentication, then route the verified test failure and exact budget
path/limit to the owning specialist. Rowan should rerun the watcher checks after
the watch service on `127.0.0.1:8788` is reachable and record a machine receipt.

