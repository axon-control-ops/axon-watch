# Agent shell Background vs true Cursor detach

**Status:** two paths — Cursor mirror (watch-only) and Axon-owned agent-terminal jobs.  
**True Cursor process handoff is blocked** — Cursor CLI does not expose background/detach.

**Related:** `agent-terminal-background-view.ts`, `agent-terminal-mirror.ts`,
`shell-terminal-session-store.ts`, `terminal/agent_jobs.py`,
`POST /api/workspaces/{id}/terminal/agent-jobs`

## What Cursor IDE does

In Cursor IDE, **Move to background** on an **in-flight** Shell tool:

1. Moves the **live OS process** into a workbench terminal tab.
2. Unblocks the agent so it can continue other tools while the shell keeps running.

Finished shell cards are history. Cursor does **not** put a re-run / continue
control on a command that already exited — short `ls`/`pwd` cards stay read-only.

## What Axon-X ships

### A) Watch in terminal (Cursor-owned shell)

Background / auto-surface on an **open** in-thread `:::terminal` block:

1. Reveals/focuses the **vaxon** agent terminal tab.
2. **Mirrors** the live transcript shell card into that xterm viewport (read-only).
3. Badge: `watching in terminal`.
4. Collapses in-thread scrollback to a receipt.
5. Does **not** take ownership of the Cursor CLI shell process.
6. Does **not** free the agent — Cursor CLI still awaits shell tool completion.

Capability flag: `CURSOR_SHELL_PROCESS_DETACH_AVAILABLE === false`.

### B) Axon-owned agent-terminal jobs (API path)

`POST /api/workspaces/{workspace_id}/terminal/agent-jobs` with `{ "command": "…" }`:

1. Ensures the persistent agent PTY (`terminal-agent` / vaxon).
2. Writes the command into that PTY (server-side `ensure_runtime`).
3. Returns a short **receipt** + `session_id` for chat/UI.
4. Operator opens the vaxon tab for live logs.

**Who can call it today:** console (`runCommandInAgentBackgroundTerminal`) and any
HTTP client. **Lane B / Cursor CLI does not call this API** — agents still use
`shellToolCall` by default and still block until that tool completes. Starting a
job here does **not** detach an already-running Cursor shell.

Console helper: `runCommandInAgentBackgroundTerminal` calls this API (falls back
to a local pending queue if control-plane is unreachable).

**Do not** re-run an in-flight Cursor shell command via this API — that duplicates
side effects. Use jobs for **new** Axon-owned work only.

## Why Cursor detach is blocked (verified 2026-07-23)

- No `--background` / `--detach` in `cursor-agent --help`.
- stream-json only emits shell tool started/completed — no PID/PTY handoff.
- `stop_run` kills the whole Cursor CLI process.

## Follow-up when Cursor exposes protocol

1. Accept detach signal for the active shell tool call id.
2. Attach live process to the agent terminal session.
3. Flip `CURSOR_SHELL_PROCESS_DETACH_AVAILABLE` to `true` → badge `backgrounded`.

## Operator-facing honesty

- Open Cursor shell: `Watch in terminal` (mirror only).
- Axon job: receipt says `Running in Axon terminal`.
- Do not claim Cursor shell “moved” into the PTY as process handoff.
