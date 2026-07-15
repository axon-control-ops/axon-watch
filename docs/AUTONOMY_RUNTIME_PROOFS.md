# Axon-X Autonomy Runtime Proofs

**Verified:** 2026-07-15
**Scope:** Strict checklist items 8–10

## Dispatch idempotency

The KAIRO converse endpoint now has a regression proof for the stale
`pending_command` path:

1. `POST /api/kairo/converse` with `health`.
2. Assert the command is `reversible_auto` and does not require confirmation.
3. `POST /api/kairo/converse` with `yes` in the same session.
4. Assert no `dispatch_command` action is returned.

The runtime router clears `pending_command` whenever a command auto-dispatches.
Only approval-gated commands retain a pending confirmation target.

Proof:
`KairoConversationEndpointTests.test_auto_dispatch_does_not_leave_endpoint_confirmation_target`.

## Health command-tier policy

The canonical policy is:

- `health`
- `check health`
- `check-health`
- `run ./scripts/dev/check-health.sh`

All four forms are read-only, `reversible_auto`, and do not require approval.
The shortcut forms normalize to the allowlisted health script before command
execution.

Proof:
`KairoConversationEndpointTests.test_health_command_variants_share_runtime_policy`
plus `VoiceAutonomyTests` and `CommandShortcutTests`.

## Run-finalization error visibility

When command execution succeeds but finalization fails:

1. Axon-X attempts to transition the run to `failed`.
2. The persisted `run_failed` receipt includes the original finalization error.
3. If that failure transition also fails, Axon-X persists a
   `finalization_error` receipt on the existing run, including `success=False`.

These proofs use the real isolated SQLite run store and inspect persisted run
history:

- `ChatOrchestrationTests.test_runtime_finalization_failure_persists_failed_receipt`
- `ChatOrchestrationTests.test_runtime_double_finalization_failure_persists_error_receipt`

## Verification

```text
./scripts/dev/python.sh -m unittest -v \
  tests.test_kairo_conversation_endpoints \
  tests.test_chat_orchestration \
  tests.test_voice_autonomy \
  tests.test_command_shortcuts \
  tests.test_run_state_transitions

Ran 38 tests in 0.192s
OK
```
