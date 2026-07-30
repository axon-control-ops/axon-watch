# Auto change → critical review → CI

**Updated:** 2026-07-30

## Goal

When any Axon-X agent finishes in-scope work and receipts for a turn, it must:

1. **Critically review** the work for factual errors, missing steps, unsupported
   assumptions, invented/unverified details, and hallucination.
2. **Cross-check** where necessary/possible against local receipts and online
   proven sources or official documentation.
3. **Suggest improvements** as a lead engineer (20+ years stance) without
   expanding scope.
4. **Rewrite** claims to be precise; never invent facts; end with
   `Confidence: X/10` (integer 1–10).
5. **Only then** may the run complete or become `review_ready`.
6. When checks apply, run CI/local verify **after** the rewrite and report **real**
   command output.
7. **Never** report bare `FAILED` — always include the failing check, file, and
   error text.

## Standing accuracy (all runtimes)

Every Ask / Plan / Debug / Agent / continuous-worker prompt also carries the
**Standing accuracy contract** from
`services/control-plane/app/workspace_agents/critical_review_clause.py`:

- lead-engineer stance (20+ years)
- never hallucinate or invent receipts
- task/goal is sole scope truth — no derail
- verify locally; consult official docs/online sources when needed
- suggest concrete improvements when they help

## Canonical Critical Review clause (all agents)

Imported from `CRITICAL_REVIEW_CLAUSE` in
`services/control-plane/app/workspace_agents/critical_review_clause.py`
(also echoed by `./scripts/ops/change-verify-loop.sh` via that module).

No role opt-out. Continuous workers, Lane B Agent / Plan / Ask / Debug, employee
persona appendices, and (when Gates 5–7 land) Lead / Verifier / independent
review / CI repair must all use the same helpers.

## Platform enforcement

- Prompt injection via `append_critical_review_clause` (includes standing accuracy).
- Employee persona appendix also embeds `AGENT_STANDING_ACCURACY_CLAUSE`.
- Lane B agent finalize and plan finalize fail-closed if `Confidence: N/10` is
  missing from the final reply (`critical_review` receipt + `failed` phase).
- Successful finalization emits a `critical_review` receipt with the score.

## Operator command

```bash
./scripts/ops/change-verify-loop.sh          # one shot
./scripts/ops/change-verify-loop.sh --watch  # poll dirty tree every 20s
./scripts/ops/change-verify-loop.sh --head-only  # verify committed HEAD only
```

## Related

- [`docs/CI_GATES.md`](../CI_GATES.md)
- [`docs/planning/GATE0-DIRTY-INVENTORY.md`](../planning/GATE0-DIRTY-INVENTORY.md)
- [`docs/AXON-X-AUTONOMY-MASTER-PLAN.md`](../AXON-X-AUTONOMY-MASTER-PLAN.md)
