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
4. While the shell is still open/streaming, chat keeps the growing scrollback visible;
   after close, mirrored cards collapse in-thread scrollback to a receipt.
5. Does **not** take ownership of the Cursor CLI shell process.
6. Does **not** free the agent — Cursor CLI still awaits shell tool completion.
7. Cursor stream-json only emits shell stdout on tool **completion** — mid-run Expo
   progress will not appear in chat for Cursor-owned shells.

Capability flag: `CURSOR_SHELL_PROCESS_DETACH_AVAILABLE === false`.

### B) Axon-owned agent-terminal jobs (API path)

`POST /api/workspaces/{workspace_id}/terminal/agent-jobs` with
`{ "command": "…", "stream_to_chat": true? }`:

1. Ensures the persistent agent PTY (`terminal-agent` / vaxon).
2. Writes the command into that PTY (server-side `ensure_runtime`).
3. Returns a short **receipt** + `session_id` for chat/UI.
4. Operator opens the vaxon tab for live logs.
5. For OTA/EAS/Expo ship commands (or explicit `stream_to_chat: true` with an
   active stream target), tees PTY chunks into an open `:::terminal` fence on the
   active Lane B / worker assistant message (exit sentinel closes the fence).
6. When the Cursor/worker turn finishes while a tee is still open, CP **defers**
   `chat_stream_done` / SSE close until the job fence settles — otherwise the
   console disconnects and mid-run deltas never arrive.

**Who can call it:** console (`runCommandInAgentBackgroundTerminal`), HTTP clients,
and agents via PATH helper `axon-agent-terminal-job` (install with
`./scripts/ops/install-bin-wrappers.sh`). Relative `./scripts/ops/...` from a
DashPro checkout will fail. Starting a job here does **not** detach an
already-running Cursor shell.

**Requirements for live chat tee:** control plane running the new code; an active
Lane B/worker stream registry entry for that workspace (agent turn in flight when
enqueue happens); `stream_to_chat` true (default for classified ship shells).

Console helper: `runCommandInAgentBackgroundTerminal` calls this API (falls back
to a local pending queue if control-plane is unreachable).

**Do not** re-run an in-flight Cursor shell command via this API — that duplicates
side effects. Use jobs for **new** Axon-owned work only.

**Honesty:** live mid-run OTA bars in chat = Axon job tee. Cursor shell cards still
dump stdout when the tool completes.

## Why Cursor detach is blocked (verified 2026-07-23)

- No `--background` / `--detach` in `cursor-agent --help`.
- stream-json only emits shell tool started/completed — no PID/PTY handoff.
- `stop_run` kills the whole Cursor CLI process.

## Follow-up when Cursor exposes protocol

1. Accept detach signal for the active shell tool call id.
2. Attach live process to the agent terminal session.
3. Flip `CURSOR_SHELL_PROCESS_DETACH_AVAILABLE` to `true` → badge `backgrounded`.

## Operator-facing honesty

- Open Cursor shell: `Watch in terminal` (mirror only; output lands on completion).
- Axon job: receipt says `Running in Axon terminal`; OTA/EAS streams into chat only
  when a stream target was bound (`stream_to_chat=true` in the job record).
- Helper: `axon-agent-terminal-job --workspace <id> -- <command>`; status via
  `axon-agent-terminal-job --status <job_id> --workspace <id>`.
- Do not claim Cursor shell “moved” into the PTY as process handoff.
- Unverified until CP restart + a real canary OTA through the helper while an
  IDE stream is open.
