# MoveIT priorities — 2026-08-26

Lead: Jabulani
Retry run: `run_6c72a01d1632` (failed prior: `run_5f7fd88f9487`)

## Now

1. Land ops baseline / retry receipts under `docs/ops/` (this retry).
2. Unblock workspace delivery for MoveIT — needs Axon-X / host config; Lead cannot create delivery policy; handoff POST needs operator bearer token.
3. Clear Remy’s waiting_approval decision about the failed lead shift once delivery is fixed or Sir King accepts the blocker.

## Next (only after delivery publishes)

1. First product slice: Reed schema/API + Ayesha thin shell — concrete acceptance criteria per assign.
2. Sol wires minimum connectors against ready service bridge.
3. Remy runs MVP verification plan (`docs/ops/mvp-verification-plan.md`).

## Done since last priorities note

- `package.json` / `package-lock.json` are real files (no longer empty directories).
- Service connection reports `ready=true` (vault unlocked; operator `.env` still optional/absent).

## Explicit non-goals this turn

- No commit/push.
- No specialist implementation in foreign trees.
- No fake “agents started” claims without new task/run ids.
- No self-assigned Lead task.
