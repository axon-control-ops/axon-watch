# Auto change → critical review → CI

**Updated:** 2026-07-20

## Goal

When any Axon-X agent finishes in-scope work and receipts for a turn, it must:

1. **Critically review** the work for factual errors, missing steps, unsupported
   assumptions, and invented/unverified details.
2. **Rewrite** claims to be precise; end with `Confidence: X/10` (integer 1–10).
3. **Only then** may the run complete or become `review_ready`.
4. When checks apply, run CI/local verify **after** the rewrite and report **real**
   command output.
5. **Never** report bare `FAILED` — always include the failing check, file, and
   error text.

## Canonical clause (all agents)

> Critically review all your previous work for factual errors, missing steps, unsupported assumptions, and any invented or unverified details. Then rewrite the answer to correct those issues and make it more precise and reliable. End with Confidence: X/10.

Shared implementation: `services/control-plane/app/workspace_agents/critical_review_clause.py`.

No role opt-out. Continuous workers, Lane B Agent / Plan / Ask / Debug, and (when
Gates 5–7 land) Lead / Verifier / independent review / CI repair must all use the
same helper. Verifier narratives must also end with Confidence even after pass/fail
evidence.

## Platform enforcement

- Prompt injection via `append_critical_review_clause`.
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
