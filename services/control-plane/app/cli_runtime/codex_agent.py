"""Local Codex CLI runtime adapter for IDE composer requests."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy
from app.cli_runtime.stream_blocks.terminal_blocks import _relative_path, terminal_block
from app.cli_runtime.subprocess_runner import (
    RuntimeProcessStoppedError,
    communicate_registered_process,
    raise_if_operator_stopped,
    stream_registered_process,
)


def _build_codex_exec_command(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    reasoning_effort: str = "",
    outer_sandboxed: bool = False,
) -> list[str]:
    # Safe-improvement evaluation must pass the disposable isolation root here
    # (see proposal_service.sandbox_agent_workspace), never the live bound project.
    command = [binary, "exec", "--json", "--ephemeral"]
    if workspace_root:
        command.extend(["-C", str(workspace_root), "--skip-git-repo-check"])
    if execution_tier == "executing":
        # Continuous workers are already contained by Axon's per-run Bubblewrap
        # sandbox and immutable shell hooks. Nesting Codex's workspace-write
        # sandbox inside that boundary blocks approved wrapper callbacks such
        # as axon-agent-terminal-job (localhost control-plane enqueue), leaving
        # long-running ship jobs unable to create their Axon-owned PTY job.
        #
        # Keep Codex unrestricted only inside the outer Axon sandbox; the outer
        # sandbox still enforces writable paths, approved wrappers, hidden
        # metadata mounts, and process cancellation. It also removes the need
        # for nested per-command approvals on routine pre-approved work.
        codex_sandbox = "danger-full-access" if outer_sandboxed else "workspace-write"
        approval = "never" if outer_sandboxed else "on-request"
        command.extend(["--sandbox", codex_sandbox, "-c", f'approval_policy="{approval}"'])
    else:
        command.extend(["--sandbox", "read-only", "-c", 'approval_policy="never"'])
    if model:
        command.extend(["--model", model])
    if reasoning_effort:
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
    command.append("--")
    command.append(prompt)
    return command


def _iter_codex_payloads(stream_text: str) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for raw_line in str(stream_text or "").splitlines():
        try:
            payload = json.loads(raw_line.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _diff_counts(diff: str) -> tuple[int, int]:
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return added, removed


def _codex_item_block(item: dict[str, object], workspace_root: Path) -> str:
    """Translate Codex JSON items into the transcript grammar used by every UI.

    Codex emits real command/file events, but the old adapter retained only the
    final agent_message. Keeping them here gives all workspace threads the same
    terminal, file-change, and expandable-diff cards already used by Cursor.
    """
    item_type = str(item.get("type") or "").strip()
    if item_type == "command_execution":
        command = str(item.get("command") or "").strip()
        if command:
            # Codex reports a command as an ``item.started`` well before it
            # completes. Keep an open terminal card in the live transcript so
            # Full Access never looks like an inert text-only response.
            if str(item.get("_axon_event_type") or "").strip().lower() == "item.started" or str(item.get("status") or "").strip().lower() in {
                "in_progress",
                "running",
            }:
                return f"\n:::terminal {command}\n# Running…\n:::\n"
            return terminal_block(command, str(item.get("aggregated_output") or ""))
        return ""
    if item_type == "file_change":
        changes = item.get("changes")
        if not isinstance(changes, list):
            return ":::tool File change\n"
        blocks: list[str] = []
        for change in changes:
            if not isinstance(change, dict):
                continue
            path = _relative_path(str(change.get("path") or ""), str(workspace_root)) or "changed file"
            diff = str(change.get("diff") or change.get("patch") or "").strip()
            added, removed = _diff_counts(diff)
            blocks.append(f"\n:::edit {path} +{added} -{removed}\n{diff}\n:::\n")
        return "".join(blocks) or ":::tool File change\n"
    if item_type == "error":
        detail = str(item.get("message") or "Codex reported an unspecified runtime error.").strip()
        return f":::tool Error\n{detail}\n:::\n"
    if item_type and item_type not in {"agent_message", "reasoning"}:
        return f":::tool {item_type.replace('_', ' ').capitalize()}\n"
    return ""


def _extract_codex_text(stream_text: str, workspace_root: Path | None = None) -> str:
    final_text = ""
    item_states: dict[str, dict[str, object]] = {}
    anonymous_items: list[dict[str, object]] = []
    saw_json = False
    root = workspace_root or Path.cwd()
    for payload in _iter_codex_payloads(stream_text):
        saw_json = True
        if payload.get("type") == "error":
            message = str(payload.get("message") or "").strip()
            if message:
                anonymous_items.append({"type": "error", "message": message})
            continue
        if payload.get("type") not in {"item.started", "item.updated", "item.completed"}:
            continue
        raw_item = payload.get("item")
        if not isinstance(raw_item, dict):
            continue
        item = {**raw_item, "_axon_event_type": str(payload.get("type") or "")}
        item_id = str(item.get("id") or "").strip()
        if item_id:
            item_states[item_id] = item
        else:
            anonymous_items.append(item)
    if not saw_json:
        return str(stream_text or "").strip()
    blocks: list[str] = []
    for item in (*item_states.values(), *anonymous_items):
        if item.get("type") == "agent_message":
            text = str(item.get("text") or "").strip()
            if text:
                final_text = text
            continue
        block = _codex_item_block(item, root)
        if block:
            blocks.append(block)
    transcript = "".join(blocks).strip()
    return "\n\n".join(part for part in (transcript, final_text) if part).strip()


def run_codex_local(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    reasoning_effort: str = "",
    timeout_seconds: int = 90,
    subprocess_env: dict[str, str] | None = None,
    run_id: str = "",
    on_chunk: Callable[[str, str], None] | None = None,
    sandbox_policy: AgentSandboxPolicy | None = None,
) -> str:
    command = _build_codex_exec_command(
        binary=binary,
        prompt=prompt,
        workspace_root=workspace_root,
        composer_mode=composer_mode,
        execution_tier=execution_tier,
        model=model,
        reasoning_effort=reasoning_effort,
        outer_sandboxed=sandbox_policy is not None,
    )

    def _emit_codex_chunk(accumulated: str, delta: str) -> None:
        if on_chunk is None:
            return
        extracted = _extract_codex_text(accumulated, workspace_root)
        if extracted:
            on_chunk(extracted, delta)

    runner = stream_registered_process if on_chunk is not None else communicate_registered_process
    try:
        stdout, stderr, returncode = runner(
            run_id=run_id,
            command=command,
            timeout_seconds=timeout_seconds,
            subprocess_env=subprocess_env,
            cwd=str(workspace_root),
            sandbox_policy=sandbox_policy,
            **({"on_chunk": _emit_codex_chunk} if on_chunk is not None else {}),
        )
    except RuntimeProcessStoppedError:
        raise
    except RuntimeError:
        raise
    raise_if_operator_stopped(returncode=returncode, stderr=stderr, stdout=stdout)
    output = _extract_codex_text(stdout, workspace_root)
    if not output:
        output = stdout.strip() or stderr.strip()
    if returncode != 0:
        raise RuntimeError(output or f"Codex CLI exited with status {returncode}.")
    if not output:
        raise RuntimeError("Codex CLI returned no output.")
    return output
