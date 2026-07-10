# Agent shell Background vs true Cursor detach

**Status:** mirror UX shipped; true process detach blocked on Cursor CLI protocol.  
**Related:** `agent-terminal-background-view.ts`, `agent-terminal-mirror.ts`, `useAgentTerminalMirror.ts`, `shell-terminal-session-store.ts`

## What Cursor does

In Cursor IDE, **Run in Background** on an in-flight Shell tool:

1. Moves the live command into a workbench terminal tab.
2. Unblocks the agent so it can continue other tools while the shell keeps running.

## What Axon-X ships today

Background on an open in-thread `:::terminal` block:

1. Reveals/focuses the **vaxon** agent terminal tab.
2. **Mirrors** the live transcript shell card into that xterm viewport (read-only snapshot stream).
3. Does **not** take ownership of the Cursor CLI shell process.
4. Does **not** free the agent — Cursor CLI still awaits its own shell tool completion.

Re-running the command in an Axon PTY would duplicate side effects, so we do not spawn a second process.

## Why true detach is blocked

Shell tools are owned by the **Cursor agent CLI** stream (`shellToolCall` / `runTerminalCommandToolCall` events → `:::terminal` blocks). Axon only observes those events. There is no supported control-plane message today to:

- hand the running OS process to Axon’s PTY registry, or
- tell Cursor CLI “background this tool and continue.”

Until Cursor exposes that control, Axon cannot honestly claim Cursor-parity detach.

## Follow-up when protocol exists

1. Control-plane: accept a detach/background signal for the active shell tool call id.
2. Attach the live process (or a Cursor-provided PTY handle) to the agent terminal session.
3. Close or annotate the in-thread `:::terminal` block as backgrounded.
4. Keep Background visibility gated on an open in-thread shell (current UX).

## Operator-facing honesty

- Tab label while mirroring: `vaxon · agent shell`
- After the agent stream ends, mirror mode exits and the agent PTY websocket reconnects.
- CLEAR/ack and Sentry resolve are unrelated; do not conflate with shell Background.
