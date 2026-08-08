#!/usr/bin/env python3
"""Run deterministic real-process canaries for every employee role sandbox."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy, wrap_command_in_agent_sandbox
from app.cli_runtime.agent_shell_hook import evaluate_hook_payload
from app.workspace_agents.execution_policy import resolve_effective_policy, role_execution_policy

ROLES = ("lead", "watcher", "frontend", "backend", "integrations")


def _restore_permissions(root: Path) -> None:
    if not root.exists():
        return
    for current, directories, files in os.walk(root):
        os.chmod(current, 0o700)
        for directory in directories:
            os.chmod(Path(current) / directory, 0o700)
        for filename in files:
            os.chmod(Path(current) / filename, 0o600)


def _run_role(role: str, root: Path) -> dict[str, object]:
    workspace = root / role / "workspace"
    policy_root = root / role / "policies"
    workspace.mkdir(parents=True)
    (workspace / "README.md").write_text("sandbox canary", encoding="utf-8")
    (workspace / ".env").write_text("CANARY_SECRET=must-not-leak", encoding="utf-8")
    (workspace / "blocked").mkdir()
    baseline = role_execution_policy(role)
    task_scope = baseline.write_paths[:1]
    if task_scope:
        (workspace / task_scope[0]).mkdir(parents=True, exist_ok=True)
    effective = resolve_effective_policy(
        role=role,
        workspace_allowed_paths=(".",),
        workspace_forbidden_path_globs=("**/.env",),
        task_allowed_paths=task_scope,
    )
    sandbox_policy = AgentSandboxPolicy(
        writable_roots=effective.write_paths,
        approved_wrappers=effective.approved_wrapper_names,
        approved_command_prefixes=effective.approved_command_prefixes,
        forbidden_path_globs=effective.forbidden_path_globs,
    )
    allowed_target = (
        f"{effective.write_paths[0]}/allowed.txt"
        if effective.write_paths
        else "watcher-denied.txt"
    )
    probe = (
        "from pathlib import Path\n"
        "import json\n"
        f"allowed=Path({allowed_target!r})\n"
        "result={'read':Path('README.md').read_text()=='sandbox canary'}\n"
        "try:\n allowed.write_text('ok'); result['allowed_write']=True\n"
        "except OSError:\n result['allowed_write']=False\n"
        "try:\n Path('blocked/out.txt').write_text('bad'); result['outside_denied']=False\n"
        "except OSError:\n result['outside_denied']=True\n"
        "try:\n result['secret_denied']='CANARY_SECRET' not in Path('.env').read_text()\n"
        "except OSError:\n result['secret_denied']=True\n"
        "print(json.dumps(result,sort_keys=True))\n"
    )
    launch = wrap_command_in_agent_sandbox(
        ["/usr/bin/python3", "-c", probe],
        policy=sandbox_policy,
        workspace_root=workspace,
        run_id=f"canary-{role}",
        policy_root=policy_root,
        bwrap_path="/usr/bin/bwrap",
    )
    completed = subprocess.run(
        launch.command,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{role} bwrap canary failed: {completed.stderr.strip()}")
    result = json.loads(completed.stdout)
    expected_write = bool(effective.write_paths)
    result["write_expectation_met"] = result.pop("allowed_write") is expected_write
    result["network_denied"] = (
        evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": "curl https://example.invalid"},
            approved_wrappers=frozenset(effective.approved_wrapper_names),
            approved_command_prefixes=effective.approved_command_prefixes,
        )["permission"]
        == "deny"
    )
    result["interpreter_escape_denied"] = (
        evaluate_hook_payload(
            {"hook_event_name": "beforeShellExecution", "command": "bash -c 'git status'"},
            approved_wrappers=frozenset(effective.approved_wrapper_names),
            approved_command_prefixes=effective.approved_command_prefixes,
        )["permission"]
        == "deny"
    )
    result["passed"] = all(bool(value) for value in result.values())
    return {"role": role, **result}


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="axon-role-canaries-"))
    try:
        results = [_run_role(role, root) for role in ROLES]
        print(json.dumps({"results": results}, indent=2, sort_keys=True))
        return 0 if all(bool(item["passed"]) for item in results) else 1
    finally:
        _restore_permissions(root)
        shutil.rmtree(root, ignore_errors=False)


if __name__ == "__main__":
    raise SystemExit(main())
