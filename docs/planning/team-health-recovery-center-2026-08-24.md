# Team Health Recovery Center Pass - 2026-08-24

Lead decision: open Recovery Center and triage the current attention set before
expanding autonomous dispatch.

Receipt source: `GET /api/recovery/center` at `2026-08-24T00:01:27Z`.

## Current Recovery Center State

| Bucket | Count |
| --- | ---: |
| RESUMABLE | 2 |
| ACTIVE | 3 |
| FAILED | 5 |
| RETRYABLE | 2 |

Actionable items: 9.

## Action Queue

| Workspace | Role | Run | Bucket | Class | Recovery action | Authority | Lead decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| workspace_axon_watch | lead | run_6ac2472b15bf | RESUMABLE | PROVIDER_TIMEOUT | RESUME | AUTOMATIC | Resume is permitted if Sir King wants this exact Lead task continued; otherwise leave paused because the current turn only selected Recovery Center triage. |
| workspace_axon_watch | watcher | run_eedfc0948667 | RESUMABLE | UNKNOWN | RESUME | AUTOMATIC | Do not claim watcher health from this alone; resume only after confirming the paused watcher task is still desired. |
| workspace_axon_watch | backend | run_0b01696f774a | RETRYABLE | PROVIDER_TIMEOUT | RETRY | AUTOMATIC | Reed can take one bounded retry after inspecting evidence; no broad cleanup. |
| workspace_axon_watch | integrations | run_692f71c0590d | FAILED | VERIFIER_FAILURE | INSPECT | HUMAN_APPROVAL | Quinn's failure needs verifier inspection first; do not retry until the missing worker dispatch cause is known. |
| workspace_tps | lead | run_ecbd65b76f58 | FAILED | VERIFIER_FAILURE | INSPECT | HUMAN_APPROVAL | Route to Noor; private-company-material delivery block is not an Axon-X patch. |
| workspace_tps | watcher | run_19d12203288e | FAILED | VERIFIER_FAILURE | INSPECT | HUMAN_APPROVAL | Route to Noor; missing Gate 6 evidence needs TPS-owned recovery. |
| workspace_tps | frontend | run_064e9de65de4 | FAILED | PROVIDER_TIMEOUT | RETRY | AUTOMATIC | Route to Noor before retry; TPS frontend work is outside this workspace. |
| workspace_dashpro | integrations | run_99742c01725a | RETRYABLE | UNKNOWN | HUMAN_REVIEW | HUMAN_APPROVAL | Route to Dana; unknown operator-stop cause means no invented retry. |
| workspace_dashpro | lead | run_e50b716429fa | FAILED | VERIFIER_FAILURE | INSPECT | HUMAN_APPROVAL | Route to Dana; DashPro Gate 6/out-of-scope failure belongs in the DashPro workspace. |

## Safest Next Step

1. Keep the Recovery Center open as the source of truth for this health pass.
2. Handle Axon-X-owned items first: Lead resumable, Watcher resumable, Backend
   retryable, and Integrations verifier failure.
3. Send cross-workspace items to the owning Leads instead of patching foreign
   repos from Axon-X.
4. Do not acknowledge failed verifier items as recovered until a succeeding run,
   verifier receipt, or owning Lead report exists.

## Open Risks

- No live watcher receipt was found in `docs/ops/agent-reports/`, so watcher
  health is not proven by local reports.
- Recovery Center marks some actions as automatic, but unknown cause and
  verifier failures still need human review or owning Lead routing.
- This note did not dispatch retries, resumes, commits, pushes, or cleanup work.
