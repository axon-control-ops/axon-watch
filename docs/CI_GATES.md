# Axon-X CI Gates

**Updated:** 2026-07-15

## Fast PR and push gate

Workflow: `.github/workflows/fast-gate.yml`

Job/check name: `Axon-X Fast Gate / fast-gate`

The job blocks on:

- shared contracts and backend contract modules;
- file-size and critical-hotspot ratchets;
- console typecheck, all Vitest tests, and production build;
- dependency directions, DTO budgets, ADR governance, and latency checks;
- strict handling of every non-allowlisted `PENDING` result.

Autonomy-critical modules are part of the supported contract runner and full
Vitest suite. `tests/test_ci_gate_contract.py` prevents them or the strict flag
from being silently removed.

## Nightly live-evidence gate

Workflow: `.github/workflows/nightly-verify.yml`

Job/check name: `Axon-X Nightly Strict Verify / nightly-strict`

The scheduled job starts an isolated three-service Axon-X stack, captures live
shell-boot and warm-route latency evidence, requires those files during strict
verification, uploads the evidence for 14 days, and always stops the stack.
Fixture fallback is rejected by `--require-live-evidence`.

## Local commit preflight

`scripts/sc` always runs `npm run verify:preflight`. Dependency violations, DTO
budget failures, missing strict inputs, or file-size failures abort the commit.
There is no quick bypass.

## Required-check entitlement

The repository should require `Axon-X Fast Gate / fast-gate` before merging to
`dev`. On 2026-07-15 GitHub’s branch-protection API returned `403`: private
branch protection requires a GitHub Pro upgrade or a public repository.
Therefore the workflow is installed and mandatory within CI execution, but
server-side merge enforcement remains an external entitlement blocker.
