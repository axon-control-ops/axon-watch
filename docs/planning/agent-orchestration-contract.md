# Agent Orchestration Contract (Phase G G3.1)

**Status:** Accepted thin-slice contract  
**Supersedes:** `:7734` `brain.py` ReAct as system truth (see ADR-004)

## Flow

```text
Operator intent (command or IDE composer)
    → control-plane persisted run (phases, approvals, receipts)
    → runtime fabric (Cursor primary, Codex fallback)
    → normalized chat messages + run receipts
    → review_ready / complete
```

## Surfaces

| Surface | Thread kind | Composer modes | Dispatch |
|---|---|---|---|
| Operator Command | `operator` | `command` (default) | Command executor → run |
| IDE Agent Dock | `ide` | `ask`, `plan`, `agent` | Lane B → CLI runtime |

## Execution tiers (G3.3 / G3.8)

| Tier | API field | CLI behavior | Approval |
|---|---|---|---|
| Consultative | `execution_access: consultative` | Cursor plan / Codex read-only | None for Ask/Plan; Agent run optional |
| Full Access | `execution_access: full` | Cursor agent / Codex workspace-write | Run `awaiting_approval` → approve → `executing` |

## Run phases (source of truth)

Persisted in SQLite via `run_store` — not inferred from transcript.

Blocked execution when phase ≠ `executing`:

- `orchestrate_command_run` (operator commands)
- `approval_gate.resolve_runtime_execution_tier` (CLI fabric)

## Receipts

| Event | Receipt type |
|---|---|
| CLI dispatch | `runtime_dispatch` |
| Command exec | `command_execution` |
| Approval | `approval_requested`, `operator_approve`, `operator_reject` |
| Review pause | `review_ready` |
| Stop | `operator_stop` |

## References

- `services/control-plane/app/chat/service.py`
- `services/control-plane/app/cli_runtime/approval_gate.py`
- `services/control-plane/app/cli_runtime/router.py`
- `docs/PHASE_G_SIGNAL_PARITY.md` (G3 slices)
- `docs/planning/ADR-004-execution-state-model.md`
