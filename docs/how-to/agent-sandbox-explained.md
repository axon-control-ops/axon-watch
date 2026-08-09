# Agent sandbox — what it is, how it works, and what to do when it breaks

**Read this when:** an agent run fails with a sandbox or `bwrap` error, you
want to understand what those `/tmp/axon-si-run_*` directories are, or you
need to tune sandbox permissions for a workspace.

**Last updated:** 2026-08-09

---

## 1. The short answer — what is the sandbox?

When Axon-X dispatches a Cursor, Claude, or Codex agent to work on a
workspace, it does not let that agent loose on your real files. Instead it:

1. Makes a **disposable copy** of the workspace (the "checkout") in `/tmp`.
2. Runs the CLI **inside a container-like jail** (Bubblewrap) that can only
   see that copy.
3. Enforces a **policy file** that lists exactly which paths inside the
   checkout the agent is allowed to write.
4. Cleans up the temporary directory when the run ends — or leaves it behind
   if the run crashed (see §5).

The result is that agent mistakes stay inside `/tmp` and never touch your
real working tree or any other file on the host.

---

## 2. The pieces, one by one

### 2a. The disposable checkout

Each agent run gets its own directory under `/tmp`:

```
/tmp/axon-si-run_<run-id>/checkout/
```

This is a fresh, independent copy of the workspace at the time the run
started. The agent reads and writes inside here. Nothing it does can affect
your real repository until a passing run deliberately creates a pull request.

### 2b. Bubblewrap (`bwrap`) — the actual container

[Bubblewrap](https://github.com/containers/bubblewrap) is a lightweight
Linux tool that creates an isolated namespace for a process, similar to
Docker but with no daemon and very low overhead. Axon-X calls it like this
(simplified):

```
bwrap \
  --die-with-parent        # kill agent if control-plane dies
  --unshare-pid            # agent can't see other processes
  --cap-drop ALL           # drop all Linux capabilities
  --ro-bind /checkout /checkout   # workspace visible, read-only
  --bind /checkout/docs   /checkout/docs   # this folder is writable
  --tmpfs /tmp             # agent gets an empty /tmp
  -- cursor agent ...
```

The agent process runs inside this bubble. It can read the whole checkout
but can only **write** to the specific directories listed in the policy.

### 2c. The policy file

Before the run starts, the control plane writes a read-only JSON file at:

```
/run/user/<uid>/axon-watch/agent-sandbox-policies/run-<hash>/policy.json
```

It looks like this:

```json
{
  "version": 1,
  "approved_wrappers": ["git", "npm"],
  "approved_command_prefixes": [["npm", "test"], ["git", "commit"]],
  "forbidden_path_globs": ["secrets/**", ".env*"]
}
```

- **`approved_wrappers`** — shell tools the agent is allowed to call.
- **`approved_command_prefixes`** — specific commands the agent may run
  (e.g. `npm test` is allowed but `npm publish` is not).
- **`forbidden_path_globs`** — paths inside the checkout that are hidden
  from the agent entirely, even for reading (bound to an empty tmpfs).

A hook script (`hook.py`) enforces this policy on every shell command the
agent tries to run, before execution. If the command is not on the approved
list, the hook kills it — "fail closed".

### 2d. The writable roots

The policy also specifies which paths inside the checkout the agent can
write to. Everything else is read-only. A typical specialist worker might
get:

```
writable_roots: ["docs/ops", "tests"]
```

That means the agent can edit files under `docs/ops/` and `tests/` but
cannot modify `src/`, `config/`, `.env`, or anything else, even though it
can read them.

### 2e. The per-run scratch directories

Two special directories are bind-mounted over the checkout for agent
internal state:

| Mount point in sandbox | What it is |
|---|---|
| `/checkout/.agents` | Cursor/Claude internal scratch (session state) |
| `/checkout/.codex` | Codex internal scratch |

These are **empty per-run directories** from the policy root, not your real
`.agents` or `.codex` folders. Any state the agent writes there disappears
when the run ends — it never lands in a commit.

---

## 3. How a run flows end-to-end

```
Axon-X leases a task
  │
  ▼
Control plane resolves:
  • which workspace (checkout path)
  • which runtime (cursor / claude / codex)
  • which writable_roots (from task allowed_paths)
  • which approved_wrappers
  │
  ▼
agent_sandbox.py creates:
  /tmp/axon-si-run_<id>/checkout/   ← disposable copy
  /run/user/.../run-<hash>/         ← policy + hook files
  │
  ▼
bwrap launches CLI inside bubble:
  • read-only workspace
  • writable_roots bound read-write
  • policy hook enforcing every shell call
  │
  ▼
Agent works, creates commits inside /tmp
  │
  ▼
Run ends (pass / fail / cancelled)
  │
  ├─ PASS: control plane publishes draft PR from the /tmp commits
  └─ FAIL: checkout left in /tmp for inspection, policy dir cleaned up
```

---

## 4. Runtime controls in Settings → CLI runtime

In **Settings → CLI runtime** you can control:

### Which runtimes are allowed to run AUTO mode

AUTO (full-autonomy) worker shifts consume real quota. You can restrict
which CLIs are allowed to be used for autonomous background shifts:

- **All runtimes** — any signed-in runtime (Cursor, Claude, Codex) may run
  worker shifts when the scheduler is on.
- **Cursor only** — only Cursor CLI dispatches autonomous shifts; Claude
  and Codex are restricted to operator-initiated runs.
- **Claude only** — only Claude Code CLI runs autonomous shifts.
- **Custom** — pick any combination per workspace.

This does not affect which runtime you manually pick in the Agent Dock — it
only gates the **scheduler's** automatic dispatch.

### Workspace runtime concurrency

Controls how many runtimes can run **simultaneously** for a single workspace:

- **Single (1)** — only one agent shift runs at a time per workspace,
  regardless of which runtime it uses. Simplest — no race conditions on the
  checkout.
- **Multiple** — up to `max_active` (from the Agents panel) shifts may run
  concurrently, each in its own isolated `/tmp` checkout. Faster throughput
  but uses proportionally more quota and RAM.

Default is **Single** for safety. Set to Multiple only if your workspace
has reliable Gate 6 acceptance and you've confirmed quota headroom.

---

## 5. The `/tmp/axon-si-run_*` directories

These are the disposable checkouts described above. They pile up when:

- Runs crash before the cleanup step.
- Multiple runs completed successfully but the cleanup was interrupted.
- The control plane was restarted mid-run.

**They contain no secrets and no permanent data.** Safe to delete at any
time when no agents are actively running:

```bash
# Check if any agents are currently running first:
curl -sS http://127.0.0.1:8787/api/worker-scheduler \
  | jq '{executing_count, active_run_count}'

# If executing_count is 0, clear them:
rm -rf /tmp/axon-si-run_*
```

The policy directories under `/run/user/<uid>/axon-watch/agent-sandbox-policies/`
are cleaned up automatically when runs end — you should not need to touch
those manually.

---

## 6. When things go wrong

| Error | What it means | What to do |
|---|---|---|
| `SandboxConfigurationError: Bubblewrap is required` | `bwrap` is not installed on the control-plane host | `sudo apt install bubblewrap` |
| `SandboxConfigurationError: Approved writable root escapes` | A task's `allowed_paths` tried to write outside the checkout | Check the task's scope — path must be relative to the workspace root |
| `SandboxConfigurationError: Immutable sandbox policy collision` | Two runs got the same `run_id` (should not happen) | Hard-kill and resume the scheduler; report if recurring |
| `Disposable workspace does not exist` | The `/tmp/axon-si-run_*/checkout/` was deleted while the run was starting | Run cleanup then restart; stale `/tmp` dirs can cause this if a name collides |
| Run starts but immediately fails with hook errors | The agent tried a command not in `approved_wrappers` | Check the task's role baseline — the command needs to be added to its approved list |
| Agent can't write to a file it should own | The file is in the checkout but not in `writable_roots` | Widen the task's `allowed_paths` to include that path |

---

## 7. Quick reference

```bash
# See active sandbox policy dirs
ls /run/user/$(id -u)/axon-watch/agent-sandbox-policies/ 2>/dev/null

# See live disposable checkouts
ls /tmp/axon-si-run_*/ 2>/dev/null | head -20

# Count stale checkouts
ls /tmp/ | grep axon-si-run | wc -l

# Safe cleanup (only when no agents are executing)
rm -rf /tmp/axon-si-run_*

# Check if bwrap is available
which bwrap && bwrap --version
```

---

Related:

- [`auto-loop-and-credits.md`](auto-loop-and-credits.md) — quota planning for agent shifts
- [`autonomy-gates-and-service-identity.md`](autonomy-gates-and-service-identity.md) — what governs when agents are allowed to act
- [`reliability-and-deliberate-controls.md`](reliability-and-deliberate-controls.md) — hard-kill, resume, and concurrency caps
