# Axon-X Autonomy Test Coverage

**Verified:** 2026-07-15
**Scope:** Strict checklist items 14–15

## Coverage matrix

| Concern | Primary proof |
| --- | --- |
| Dispatch idempotency | `test_kairo_conversation_endpoints.py`, `test_kairo_conversation_turns.py` |
| Action-tier defense in depth | `test_voice_autonomy.py`, `conversation-command-policy.test.ts` |
| Run-state transitions and failure receipts | `test_run_state_transitions.py`, `test_chat_orchestration.py` |
| Typed/voice KAIRO parity | `kairo-conversation-submit-parity.test.ts`, `kairo-speech-session.test.ts` |
| Evidence and autonomy projection | `operator-evidence-projector.test.ts` |
| Voice persistence failures | `test_conversation_transcript.py`, `test_voice_transcript_store.py` |

The browser policy requires both `requires_confirmation === false` and
`action_tier === "reversible_auto"` before auto-dispatch. An inconsistent or
missing tier is fail-closed.

## Debug ingest gate

Debug session ingest has no live frontend call sites and is disabled by
default:

- Backend route and Python helper require `AXON_DEBUG_SESSION_LOG=1`.
- Frontend helper requires a non-production build and
  `VITE_AXON_DEBUG_SESSION_LOG=1`.
- Disabled API requests return `404`.

Enable both variables only for a bounded evidence-first debug session, then
remove them from the runtime environment.

## Verification

```text
npm run test -w @axon-watch/console-web -- --run
Test Files 166 passed (166)
Tests 744 passed (744)

npm run verify:contracts
All contract modules passed, including the endpoint, transcript-failure,
voice-store, and debug-gate modules.
```
