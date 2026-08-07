from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_sandbox import (  # noqa: E402
    AgentSandboxPolicy,
    SandboxConfigurationError,
    build_bwrap_command,
    materialize_cursor_hook_policy,
    wrap_command_in_agent_sandbox,
)
from app.cli_runtime.agent_shell_hook import evaluate_hook_payload, run_hook  # noqa: E402


def _make_tree_removable(root: Path) -> None:
    if not root.exists():
        return
    for current, directories, files in os.walk(root):
        os.chmod(current, 0o700)
        for directory in directories:
            os.chmod(Path(current) / directory, 0o700)
        for filename in files:
            os.chmod(Path(current) / filename, 0o600)


class AgentSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="axon-agent-sandbox-test-"))
        self.workspace = self.temp_root / "workspace"
        self.workspace.mkdir()
        # Bubblewrap reserves .agents only in disposable worker/composer
        # checkouts; this fixture models that boundary.
        (self.workspace / ".axon-si").mkdir()
        (self.workspace / "write").mkdir()
        (self.workspace / "readonly").mkdir()
        (self.workspace / ".env").write_text("TOP_SECRET=value", encoding="utf-8")
        self.home = self.temp_root / "home"
        (self.home / ".cursor").mkdir(parents=True)
        (self.home / ".cursor" / "auth.json").write_text("{}", encoding="utf-8")
        self.policy_root = self.temp_root / "policies"

    def tearDown(self) -> None:
        _make_tree_removable(self.temp_root)
        shutil.rmtree(self.temp_root, ignore_errors=False)

    def _policy(self, **overrides: object) -> AgentSandboxPolicy:
        values: dict[str, object] = {
            "writable_roots": ("write",),
            "approved_wrappers": ("axon-test",),
            "approved_command_prefixes": (("git", "status"), ("pytest", "-q")),
            "cursor_readonly_paths": (str(self.home / ".cursor" / "auth.json"),),
            "forbidden_path_globs": ("**/.env",),
        }
        values.update(overrides)
        return AgentSandboxPolicy(**values)  # type: ignore[arg-type]

    def _material(self, policy: AgentSandboxPolicy | None = None):
        return materialize_cursor_hook_policy(
            policy=policy or self._policy(),
            run_id="run-sandbox-1",
            workspace_root=self.workspace,
            policy_root=self.policy_root,
        )

    def test_no_policy_leaves_command_unwrapped(self) -> None:
        with patch(
            "app.cli_runtime.agent_sandbox.require_bubblewrap",
            side_effect=AssertionError("must not probe bwrap"),
        ):
            launch = wrap_command_in_agent_sandbox(
                ["/bin/echo", "ok"],
                policy=None,
                workspace_root=self.workspace,
                run_id="",
            )
        self.assertEqual(("/bin/echo", "ok"), launch.command)
        self.assertIsNone(launch.hook_material)

    def test_policy_requires_bubblewrap_fail_closed(self) -> None:
        with patch("app.cli_runtime.agent_sandbox.shutil.which", return_value=None):
            with self.assertRaisesRegex(SandboxConfigurationError, "Bubblewrap is required"):
                wrap_command_in_agent_sandbox(
                    ["/bin/echo", "must-not-run"],
                    policy=self._policy(),
                    workspace_root=self.workspace,
                    run_id="run-no-bwrap",
                    policy_root=self.policy_root,
                )
        self.assertFalse(self.policy_root.exists())

    def test_materialized_hooks_are_deterministic_read_only_and_external(self) -> None:
        first = self._material()
        second = self._material()
        self.assertEqual(first, second)
        self.assertFalse(first.root.is_relative_to(self.workspace))
        hooks = json.loads(first.hooks_json.read_text(encoding="utf-8"))
        self.assertTrue(hooks["hooks"]["beforeShellExecution"][0]["failClosed"])
        self.assertTrue(hooks["hooks"]["preToolUse"][0]["failClosed"])
        self.assertEqual("Shell", hooks["hooks"]["preToolUse"][0]["matcher"])
        self.assertEqual(0o444, stat.S_IMODE(first.hooks_json.stat().st_mode))
        self.assertEqual(0o444, stat.S_IMODE(first.policy_json.stat().st_mode))
        self.assertEqual(0o555, stat.S_IMODE(first.hook_script.stat().st_mode))
        self.assertEqual(0o555, stat.S_IMODE(first.root.stat().st_mode))

    def test_builtin_terminal_wrapper_never_uses_a_workspace_path(self) -> None:
        workspace_wrapper = self.workspace / "bin" / "axon-agent-terminal-job"
        workspace_wrapper.parent.mkdir()
        workspace_wrapper.write_text("#!/bin/sh\necho compromised\n", encoding="utf-8")
        workspace_wrapper.chmod(0o755)
        policy = self._policy(approved_wrappers=("axon-agent-terminal-job",))

        with patch(
            "app.cli_runtime.agent_sandbox.shutil.which",
            return_value=str(workspace_wrapper),
        ):
            material = self._material(policy)

        wrapper = material.root / "bin" / "axon-agent-terminal-job"
        source = wrapper.read_text(encoding="utf-8")
        self.assertTrue(wrapper.is_file())
        self.assertEqual(0o555, stat.S_IMODE(wrapper.stat().st_mode))
        self.assertNotIn(str(workspace_wrapper), source)
        self.assertNotIn("compromised", source)

    def test_workspace_agents_scratch_is_private_and_mountable(self) -> None:
        material = self._material()
        command = build_bwrap_command(
            ["/bin/true"],
            policy=self._policy(),
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        self.assertTrue((self.workspace / ".agents").is_dir())
        self.assertFalse(any((self.workspace / ".agents").iterdir()))
        self.assertTrue((self.workspace / ".codex").is_dir())
        self.assertFalse(any((self.workspace / ".codex").iterdir()))
        self.assertIn(str(material.workspace_scratch), command)
        self.assertIn(str(material.workspace_codex_scratch), command)
        self.assertIn(str(self.workspace / ".agents"), command)
        self.assertIn(str(self.workspace / ".codex"), command)

    def test_workspace_agents_scratch_supports_a_selected_ide_workspace(self) -> None:
        ordinary = self.temp_root / "ordinary-workspace"
        ordinary.mkdir()
        material = materialize_cursor_hook_policy(
            policy=self._policy(),
            run_id="run-ordinary-workspace",
            workspace_root=ordinary,
            policy_root=self.policy_root,
        )
        command = build_bwrap_command(
            ["/bin/true"],
            policy=self._policy(),
            workspace_root=ordinary,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        self.assertTrue((ordinary / ".agents").is_dir())
        self.assertTrue((ordinary / ".codex").is_dir())
        self.assertIn(str(ordinary / ".agents"), command)
        self.assertIn(str(ordinary / ".codex"), command)

    def test_policy_material_cannot_be_written_inside_workspace(self) -> None:
        with self.assertRaisesRegex(SandboxConfigurationError, "outside the workspace"):
            materialize_cursor_hook_policy(
                policy=self._policy(),
                run_id="run-bad-policy-root",
                workspace_root=self.workspace,
                policy_root=self.workspace / ".policy",
            )

    def test_materialized_hook_script_enforces_its_policy(self) -> None:
        material = self._material()
        for command, expected in (
            ("axon-test unit", "allow"),
            ("curl https://example.invalid", "deny"),
        ):
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, material.hook_script, material.policy_json],
                    input=json.dumps(
                        {
                            "hook_event_name": "beforeShellExecution",
                            "command": command,
                        }
                    ),
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(expected, json.loads(result.stdout)["permission"])

    def test_bwrap_command_has_private_namespaces_and_narrow_mounts(self) -> None:
        policy = self._policy()
        material = self._material(policy)
        command = build_bwrap_command(
            ["/bin/echo", "ok"],
            policy=policy,
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        for option in ("--unshare-pid", "--unshare-ipc", "--unshare-uts", "--tmpfs"):
            self.assertIn(option, command)
        self.assertNotIn("--unshare-net", command)
        self.assertNotIn("/", [
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value in {"--ro-bind", "--bind"}
        ])
        self.assertIn(str(self.workspace), command)
        self.assertIn(str(self.workspace / "write"), command)
        self.assertIn(str(self.home / ".cursor" / "auth.json"), command)
        self.assertIn("/run/axon-agent-home/.cursor/hooks.json", command)
        self.assertEqual(["/bin/echo", "ok"], command[-2:])

    def test_symlinked_binary_resolves_to_its_real_target(self) -> None:
        """npm/nvm-managed CLIs are commonly invoked via a symlink (e.g.
        ~/.local/bin/cursor-agent -> .../versions/<ver>/cursor-agent).
        cursor_readonly_paths is computed by resolving that same chain to
        its real target directory (see sandbox_policy_adapter._runtime_paths)
        — if the command execs the *unresolved* symlink path instead, bwrap
        can't find it (only the resolved target was bind-mounted), so every
        sandboxed run of a symlinked CLI failed with "No such file or
        directory" before this resolution was added here too.
        """
        real_dir = self.home / "real" / "v1"
        real_dir.mkdir(parents=True)
        real_binary = real_dir / "tool"
        real_binary.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        real_binary.chmod(0o755)
        symlink_binary = self.temp_root / "tool-shim"
        symlink_binary.symlink_to(real_binary)

        policy = self._policy(cursor_readonly_paths=(str(real_dir),))
        material = self._material(policy)
        command = build_bwrap_command(
            [str(symlink_binary), "--flag"],
            policy=policy,
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        self.assertEqual([str(real_binary), "--flag"], command[-2:])

    def test_writable_root_rejects_parent_and_symlink_escapes(self) -> None:
        outside = self.temp_root / "outside"
        outside.mkdir()
        (self.workspace / "link").symlink_to(outside, target_is_directory=True)
        material = self._material()
        for escape in ("../outside", "link"):
            with self.subTest(escape=escape):
                with self.assertRaisesRegex(SandboxConfigurationError, "escapes"):
                    build_bwrap_command(
                        ["/bin/true"],
                        policy=self._policy(writable_roots=(escape,)),
                        workspace_root=self.workspace,
                        hook_material=material,
                        bwrap_path="/usr/bin/bwrap",
                        user_home=self.home,
                    )

    def test_missing_writable_root_is_created_instead_of_failing_dispatch(self) -> None:
        """Role-baseline writable roots (e.g. "docs/ops") are the same for every
        workspace regardless of that project's actual directory layout — a
        workspace that simply hadn't created the directory yet used to fail
        every dispatch outright. It's an already-approved write target, so
        create it rather than treating "not created yet" as fatal.
        """
        material = self._material(self._policy(writable_roots=("docs/ops",)))
        self.assertFalse((self.workspace / "docs" / "ops").exists())
        command = build_bwrap_command(
            ["/bin/true"],
            policy=self._policy(writable_roots=("docs/ops",)),
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        self.assertTrue((self.workspace / "docs" / "ops").is_dir())
        self.assertIn(str(self.workspace / "docs" / "ops"), command)

    def test_writable_root_rejects_missing_escape_without_creating_it(self) -> None:
        material = self._material()
        outside = self.temp_root / "outside-missing"
        self.assertFalse(outside.exists())
        with self.assertRaisesRegex(SandboxConfigurationError, "escapes"):
            build_bwrap_command(
                ["/bin/true"],
                policy=self._policy(writable_roots=("../outside-missing",)),
                workspace_root=self.workspace,
                hook_material=material,
                bwrap_path="/usr/bin/bwrap",
                user_home=self.home,
            )
        self.assertFalse(outside.exists())

    def test_writable_root_can_narrow_to_an_existing_file(self) -> None:
        (self.workspace / "docs").mkdir()
        target = self.workspace / "docs" / "ops"
        target.write_text("before", encoding="utf-8")
        material = self._material(self._policy(writable_roots=("docs/ops",)))
        command = build_bwrap_command(
            ["/bin/true"],
            policy=self._policy(writable_roots=("docs/ops",)),
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        self.assertIn(str(target), command)

    def test_cursor_mount_cannot_shadow_run_hooks(self) -> None:
        material = self._material()
        with self.assertRaisesRegex(SandboxConfigurationError, "shadow"):
            build_bwrap_command(
                ["/bin/true"],
                policy=self._policy(
                    cursor_readonly_paths=(str(self.home / ".cursor"),)
                ),
                workspace_root=self.workspace,
                hook_material=material,
                bwrap_path="/usr/bin/bwrap",
                user_home=self.home,
            )

    @unittest.skipUnless(Path("/usr/bin/bwrap").is_file(), "Bubblewrap is unavailable")
    def test_bwrap_enforces_read_only_workspace_except_approved_root(self) -> None:
        policy = self._policy(cursor_readonly_paths=())
        launch = wrap_command_in_agent_sandbox(
            [
                "/usr/bin/python3",
                "-c",
                (
                    "from pathlib import Path\n"
                    "Path('write/allowed.txt').write_text('yes')\n"
                    "Path('.agents/runtime.txt').write_text('private')\n"
                    "Path('.codex/runtime.txt').write_text('private')\n"
                    "try:\n"
                    " Path('readonly/denied.txt').write_text('no')\n"
                    "except OSError:\n"
                    " print('DENIED')\n"
                    "try:\n"
                    " print('SECRET=' + Path('.env').read_text())\n"
                    "except OSError:\n"
                    " print('SECRET_DENIED')\n"
                ),
            ],
            policy=policy,
            workspace_root=self.workspace,
            run_id="run-bwrap-integration",
            policy_root=self.policy_root,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        result = subprocess.run(
            launch.command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("yes", (self.workspace / "write" / "allowed.txt").read_text())
        self.assertFalse((self.workspace / ".agents" / "runtime.txt").exists())
        self.assertEqual(
            "private",
            (launch.hook_material.workspace_scratch / "runtime.txt").read_text(),
        )
        self.assertFalse((self.workspace / ".codex" / "runtime.txt").exists())
        self.assertEqual(
            "private",
            (launch.hook_material.workspace_codex_scratch / "runtime.txt").read_text(),
        )
        self.assertFalse((self.workspace / "readonly" / "denied.txt").exists())
        self.assertIn("DENIED", result.stdout)
        self.assertIn("SECRET_DENIED", result.stdout)
        self.assertNotIn("TOP_SECRET", result.stdout)


class AgentShellHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.wrappers = frozenset({"axon-test", "axon-ci"})
        self.prefixes = (("git", "status"), ("pytest", "-q"))

    def _evaluate(self, command: object, *, event: str = "beforeShellExecution"):
        if event == "beforeShellExecution":
            payload = {"hook_event_name": event, "command": command}
        else:
            payload = {
                "hook_event_name": event,
                "tool_name": "Shell",
                "tool_input": {"command": command},
            }
        return evaluate_hook_payload(
            payload,
            approved_wrappers=self.wrappers,
            approved_command_prefixes=self.prefixes,
        )

    def test_allows_only_approved_wrapper_or_token_prefix(self) -> None:
        self.assertEqual("allow", self._evaluate("axon-test unit frontend")["permission"])
        self.assertEqual("allow", self._evaluate("git status --short")["permission"])
        self.assertEqual("allow", self._evaluate("pytest -q tests/unit")["permission"])
        self.assertEqual("deny", self._evaluate("pytest tests/unit")["permission"])
        self.assertEqual("deny", self._evaluate("/tmp/axon-test unit")["permission"])

    def test_blocks_shell_network_privilege_git_and_interpreter_bypasses(self) -> None:
        denied_commands = (
            "axon-test ok; curl https://example.invalid",
            "axon-test $(curl https://example.invalid)",
            "axon-test `id`",
            "axon-test > /tmp/result",
            "axon-test && axon-ci",
            "axon-test ../*",
            "curl https://example.invalid",
            "/usr/bin/wget https://example.invalid",
            "sudo axon-test",
            "bash -c axon-test",
            "python3 -c 'import os; os.system(\"axon-test\")'",
            "env axon-test",
            "command axon-test",
            "git reset --hard",
            "git -C . push origin main",
            "git -c alias.pwn='!sh' pwn",
            "git diff --no-index /home/edp/.config/Cursor/User/globalStorage/state.vscdb x",
            "rg token ../secrets",
            "find . -exec axon-test {} ;",
        )
        for command in denied_commands:
            with self.subTest(command=command):
                self.assertEqual("deny", self._evaluate(command)["permission"])

    def test_pre_tool_use_fails_closed_on_missing_or_wrong_shape(self) -> None:
        self.assertEqual(
            "allow",
            self._evaluate("axon-ci fast-gate", event="preToolUse")["permission"],
        )
        malformed = (
            {"hook_event_name": "preToolUse", "tool_name": "Shell", "tool_input": {}},
            {"hook_event_name": "preToolUse", "tool_name": "Read", "tool_input": {}},
            {"hook_event_name": "unknown", "command": "axon-test"},
        )
        for payload in malformed:
            with self.subTest(payload=payload):
                response = evaluate_hook_payload(
                    payload,
                    approved_wrappers=self.wrappers,
                    approved_command_prefixes=self.prefixes,
                )
                self.assertEqual("deny", response["permission"])

    def test_hook_policy_io_and_json_errors_fail_closed(self) -> None:
        missing = Path("/definitely/missing/agent-policy.json")
        self.assertEqual("deny", run_hook(missing, "{}")["permission"])
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "policy.json"
            malformed.write_text("{", encoding="utf-8")
            self.assertEqual(
                "deny",
                run_hook(
                    malformed,
                    '{"hook_event_name":"beforeShellExecution","command":"axon-test"}',
                )["permission"],
            )


if __name__ == "__main__":
    unittest.main()
