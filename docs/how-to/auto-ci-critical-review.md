# Auto change → critical review → CI

**Updated:** 2026-07-18

## Goal

When code changes, an agent (or operator) must:

1. **Critically review** the work for factual errors, missing steps, unsupported
   assumptions, and invented/unverified details.
2. **Rewrite** claims to be precise; end with `Confidence: X/10`.
3. **Only then** run CI/local verify and report **real** command output.
4. **Never** report bare `FAILED` — always include the failing check, file, and
   error text.

## Operator command

```bash
./scripts/ops/change-verify-loop.sh          # one shot
./scripts/ops/change-verify-loop.sh --watch  # poll dirty tree every 20s
```

## Company team workers

Continuous worker prompts for `watcher` / `backend` / `integrations` include the
same critical-review → verify clause. Failure receipts must carry the reason
(e.g. Cursor usage limit), and the company roster shows
`Last shift failed: <reason>` instead of a silent fail.

## Related

- [`docs/CI_GATES.md`](../CI_GATES.md)
- [`docs/how-to/ci-merge-and-worker-agents.md`](ci-merge-and-worker-agents.md) (when present on branch)
