# Agent shell Background vs true Cursor detach

**Status:** mirror UX is the shipped Cursor-parity ceiling.  
**True process handoff is blocked** — Cursor CLI does not expose background/detach.

**Related:** `agent-terminal-background-view.ts`, `agent-terminal-mirror.ts`,
`useAgentTerminalMirror.ts`, `shell-terminal-session-store.ts`,
`agent-terminal-open.ts`

## What Cursor IDE does

In Cursor IDE, **Move to background** on an **in-flight** Shell tool:

1. Moves the **live OS process** into a workbench terminal tab.
2. Unblocks the agent so it can continue other tools while the shell keeps running.

Finished shell cards are history. Cursor does **not** put a re-run / continue
control on a command that already exited — short `ls`/`pwd` cards stay read-only.

## What Axon-X ships (honest ceiling)

Background / auto-surface on an **open** in-thread `:::terminal` block:

1. Reveals/focuses the **vaxon** agent terminal tab (also auto-arms on first shell tool).
2. **Mirrors** the live transcript shell card into that xterm viewport (read-only).
3. Shows an in-thread badge: `watching in terminal`.
4. Collapses the in-thread scrollback to a receipt while the dock owns the logs
   (Expand in chat remains available).
5. Does **not** take ownership of the Cursor CLI shell process.
6. Does **not** free the agent — Cursor CLI still awaits its own shell tool completion.

Closed / finished terminal cards have **no** "Run again" CTA (Cursor parity).
Clicking the command still **reveals** a pinned snapshot of that output in vaxon;
it does not spawn a new process.

Capability flag: `CURSOR_SHELL_PROCESS_DETACH_AVAILABLE === false`
(`apps/console-web/src/lib/agent-terminal-background-view.ts`).

## Why true detach is blocked (verified 2026-07-13)

Checked `cursor-agent --help` (versions under `~/.local/share/cursor-agent/`):

- No `--background`, `--detach`, or shell-handoff flags.
- Lane B only observes `stream-json` `tool_call` `started` / `completed` for
  `shellToolCall` / `runTerminalCommandToolCall` / `terminalToolCall`.
- No PID, PTY fd, or “agent may continue” control message.
- Axon PTY registry (`pty_process.py`) can only **spawn** new shells — no
  `attach(pid)` / adopt-fd path.
- `stop_run` terminates the whole Cursor CLI process — it is not detach.

Re-running an in-flight command in an Axon PTY would duplicate side effects, so
we do not do that. Re-running a finished command from the transcript card is also
omitted — there is no Cursor equivalent and no operator need for short completed shells.

## Follow-up when Cursor exposes protocol

1. Control-plane: accept a detach/background signal for the active shell tool call id.
2. Attach the live process (or Cursor-provided PTY handle) to the agent terminal session.
3. Flip `CURSOR_SHELL_PROCESS_DETACH_AVAILABLE` to `true` and rename the badge to `backgrounded`.
4. Allow interactive input on the detached agent session.
5. Close or annotate the in-thread `:::terminal` block as backgrounded.

## Operator-facing honesty

- Tab label while mirroring: `vaxon · agent shell`
- Open-shell action: `Watch in terminal`; Cursor CLI still owns the process
- Closed-shell action: none (reveal/pin snapshot only; no re-run)
- After the agent stream ends, the mirror snapshot stays pinned (idle agent PTY does not wipe it)
- Do not claim “agent run continues in the PTY” as process handoff
