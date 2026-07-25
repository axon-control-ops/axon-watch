# Workspace Shell Commands (Transition Slice T1)

**Status:** v1 landed on `axon-watch/dev`  
**Owner:** control-plane `command_executor` + console Commands footer

## Purpose

Let Axon-X **run real workspace commands** from the operator Command seam — not
only the fixed health/read/git intents — without opening the PTY terminal.

This closes the gap between “supported commands” (footer list) and “terminal only”
for everything else during the axon-local transition.

## Operator syntax

Prefix shell work with **`run`**:

```text
run npm test
run ./scripts/dev/check-health.sh
run npm run verify:production-operator
```

Built-in intents still work without `run`:

- `health`, `ls`, `read README.md`, `git status`, `resume from review`

## UI

- Footer **Commands → Run** submits immediately (no paste-only flow).
- **Copy** keeps the old “fill Command tab” behavior.
- Conversation shows execution output in the agent reply (markdown preview when applicable).

## Safety bounds (v1)

- Executes in the **bound workspace project root** (same cwd as terminal/git status).
- **120s timeout**, output truncated at 1500 chars.
- Blocks shell metacharacters: `|`, `;`, `&&`, `sudo`, `rm -rf`, redirects, subshells.

Not a full terminal replacement — use the PTY for interactive sessions.

## Verification

```bash
PYTHONPATH=. python3 -m unittest tests.test_shell_command tests.test_command_executor
```

Live: select `axon-watch` workspace → Commands → **Run** `run npm test` or
`run ./scripts/dev/check-health.sh`.

## Next

- Allowlist common verify/dev scripts without `run` prefix (optional).
- Child-project connector commands still route to axon-local fallback per transition table.
