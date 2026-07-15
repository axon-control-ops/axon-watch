# Axon-X Self-Improvement Contract

**Version:** 1
**Status:** Defined; execution disabled pending prerequisite gates
**Owner:** Operator

## Purpose

Axon-X may propose and evaluate bounded improvements. It may not silently alter
policy, secrets, approval rules, production state, or a bound workspace. A
successful evaluation is evidence for an operator decision, not permission to
ship.

## Prerequisites

The safe-improvement API remains disabled unless all of these are true:

1. Strict checklist items 0–18 are green.
2. The operator explicitly enables the capability for a bounded session.
3. The proposed effect is supported by the current executor.
4. Exact-effect approval is unexpired and matches the proposal fingerprint.

Generic Full Access, run approval, or tool approval never substitutes for
exact-effect approval.

## Trace store

Traces are stored in the control-plane SQLite database with:

- workspace and source references;
- a human-readable summary;
- immutable receipt references;
- a redacted payload only.

Raw secrets, credentials, tokens, full environment snapshots, and unredacted
operator content are prohibited. Trace capture must fail closed when required
redaction cannot be proven.

## Evaluation dataset

An evaluation case names:

- a stable case ID and metric;
- comparator (`lte`, `gte`, or `eq`);
- baseline value;
- regression threshold;
- owner and version when promoted to a checked-in regression corpus.

Runtime-created cases are experimental evidence only. Production enablement
requires a reviewed, versioned, checked-in corpus; agents may not rewrite that
corpus or loosen thresholds.

## Verifier and thresholds

The verifier compares baseline and candidate values using the case comparator.
A regression outside the threshold sets the proposal to `failed`.

Thresholds are read from the case at evaluation time. Candidate code, proposal
payloads, and execution steps cannot override or relax them.

## Proposal workflow

Allowed state progression:

```text
draft
  -> evaluated
  -> awaiting_approval
  -> approved
  -> executing
  -> verified
  -> rolled_back
```

Any validation, approval, execution, or verification error may move the
proposal to `failed` or `rejected`. Every transition must append an
operator-visible receipt.

## Isolated execution

Evaluation and execution occur in a disposable proposal root. The bound
workspace, policy files, vault, approval configuration, deployment targets,
and production services are read-only.

The current executor is a marker-based testbed. It does not authorize real git
merge, deployment, policy mutation, secret mutation, or production mutation.
A future executor requires a separate reviewed contract revision.

## Effect policy

| Effect       | Current policy                                      |
| ------------ | --------------------------------------------------- |
| `merge`      | Evaluate and promote a marker only inside isolation |
| `policy`     | Reserved; no real mutation permitted                |
| `secret`     | Reserved; no real mutation permitted                |
| `production` | Reserved; no real mutation permitted                |

Reserved effects may be fingerprinted for workflow testing but must never be
applied to real targets.

## Approval

Approval binds:

- proposal ID;
- effect kind;
- exact target reference;
- canonical payload fingerprint;
- approving operator;
- expiry timestamp.

Execution rejects missing, expired, mismatched, or generic approvals.

## Rollback

The executor captures a baseline marker before candidate work. Rollback must:

1. restore the isolated baseline;
2. remove promoted candidate markers;
3. persist a rollback receipt;
4. set the proposal to `rolled_back`.

Rollback failure is an operator-visible failure and must never be swallowed.

## Enablement and rollback of the capability

The API is default-off. `AXON_SAFE_IMPROVEMENT_ENABLED=1` may be used only after
the prerequisites above are met and only for a bounded operator session.
Removing the variable disables the API without a data migration.

## Verification evidence

Required before any contract revision is accepted:

- trace redaction tests;
- threshold regression tests;
- isolation proof;
- exact-effect and expiry tests;
- forbidden-effect tests;
- rollback receipt tests;
- default-off and enabled-route tests;
- full contract and CI gates.

Current implementation evidence:

- `services/control-plane/app/safe_improvement/`
- `tests/test_safe_improvement.py`
- `docs/SAFE_IMPROVEMENT_SLICE.md`
