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

## Required-check enforcement

The public repository's `dev` integration branch is protected server-side.
GitHub strictly requires the `fast-gate` check before update, enforces the rule
for administrators, and disallows force-pushes and branch deletion. Fast Gate
run `29406066700` passed on commit `063cc53` before protection was enabled.

The default `master` branch predates the Fast Gate workflow and remains
unprotected. Integration and pull requests for current Axon-X work target
`dev`.
