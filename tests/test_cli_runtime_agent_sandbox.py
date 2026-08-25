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
            user_home=self.home,
        )

    def test_materialize_seeds_writable_cursor_state(self) -> None:
        config = self.home / ".cursor" / "cli-config.json"
        config.write_text('{"version":1}', encoding="utf-8")
        material = self._material()
        seeded = material.sandbox_home / ".cursor" / "cli-config.json"
        self.assertTrue(seeded.is_file())
        self.assertEqual('{"version":1}', seeded.read_text(encoding="utf-8"))

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

    def test_axon_assign_is_materialized_not_proxied_to_an_unmounted_path(self) -> None:
        """axon-assign is installed via a ~/.local/bin symlink back into the
        live repo checkout (bin/axon-assign -> .../axon-watch/bin/axon-assign),
        a path that lives outside both $HOME and the sandboxed workspace and
        is never bind-mounted. Resolving it through PATH like an ordinary
        trusted wrapper leaves a dangling symlink inside Bubblewrap, and the
        Lead's shell reports "axon-assign: not found" despite the wrapper
        being genuinely installed on the host. It must be materialized from
        the control-plane package instead, exactly like axon-agent-terminal-job.
        """
        outside_home_target = self.temp_root / "repo-checkout" / "bin" / "axon-assign"
        outside_home_target.parent.mkdir(parents=True)
        outside_home_target.write_text("#!/bin/sh\necho should-not-be-used\n", encoding="utf-8")
        outside_home_target.chmod(0o755)
        policy = self._policy(approved_wrappers=("axon-assign",))

        with patch(
            "app.cli_runtime.agent_sandbox.shutil.which",
            return_value=str(outside_home_target),
        ):
            material = self._material(policy)

        wrapper = material.root / "bin" / "axon-assign"
        self.assertTrue(wrapper.is_file())
        self.assertEqual(0o555, stat.S_IMODE(wrapper.stat().st_mode))
        source = wrapper.read_text(encoding="utf-8")
        # Not a proxy pointing at the (unmounted) resolved PATH target.
        self.assertNotIn(str(outside_home_target), source)
        self.assertNotIn("should-not-be-used", source)
        # It is the real, self-contained fan-out client.
        self.assertIn("lead/fan-out", source)
        self.assertIn("--role", source)
        self.assertIn("current workspace", source)
        self.assertIn("target_role", source)
        self.assertTrue(source.startswith("#!/usr/bin/env bash"))

        command = build_bwrap_command(
            ["axon-assign", "--workspace", "w", "--", "goal"],
            policy=policy,
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        # /run/axon-agent-policy/bin (where the materialized wrapper lives) is
        # first on PATH, so `axon-assign` resolves there instead of a dangling
        # ~/.local/bin symlink.
        path_index = command.index("PATH")
        self.assertTrue(command[path_index + 1].startswith("/run/axon-agent-policy/bin:"))
        # The unmounted external target must never be bind-mounted in either.
        self.assertNotIn(str(outside_home_target), command)

    def test_axon_assign_rejects_cross_workspace_agent_dispatch_before_network(self) -> None:
        wrapper = (
            CONTROL_PLANE_ROOT
            / "app"
            / "cli_runtime"
            / "agent_assign_wrapper.sh"
        )
        result = subprocess.run(
            [
                "bash",
                str(wrapper),
                "--workspace",
                "workspace_other",
                "--role",
                "backend",
                "--",
                "Fix persistence",
            ],
            env={**os.environ, "AXON_WATCH_WORKSPACE_ID": "workspace_demo"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("only inside their current workspace", result.stderr)

    def test_axon_runlog_is_materialized_and_curls_the_run_history_api(self) -> None:
        policy = self._policy(approved_wrappers=("axon-runlog",))
        material = self._material(policy)

        wrapper = material.root / "bin" / "axon-runlog"
        self.assertTrue(wrapper.is_file())
        self.assertEqual(0o555, stat.S_IMODE(wrapper.stat().st_mode))
        source = wrapper.read_text(encoding="utf-8")
        self.assertIn("/api/runs/", source)
        self.assertIn("/history", source)
        self.assertTrue(source.startswith("#!/usr/bin/env bash"))

        command = build_bwrap_command(
            ["axon-runlog", "run_abc123"],
            policy=policy,
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        path_index = command.index("PATH")
        self.assertTrue(command[path_index + 1].startswith("/run/axon-agent-policy/bin:"))

    def test_axonhealth_is_materialized_not_resolved_from_workspace(self) -> None:
        workspace_wrapper = self.workspace / "bin" / "axonhealth"
        workspace_wrapper.parent.mkdir(exist_ok=True)
        workspace_wrapper.write_text("#!/bin/sh\necho compromised\n", encoding="utf-8")
        workspace_wrapper.chmod(0o755)
        policy = self._policy(approved_wrappers=("axonhealth",))

        with patch(
            "app.cli_runtime.agent_sandbox.shutil.which",
            return_value=str(workspace_wrapper),
        ):
            material = self._material(policy)

        wrapper = material.root / "bin" / "axonhealth"
        self.assertTrue(wrapper.is_file())
        self.assertEqual(0o555, stat.S_IMODE(wrapper.stat().st_mode))
        source = wrapper.read_text(encoding="utf-8")
        self.assertNotIn(str(workspace_wrapper), source)
        self.assertNotIn("compromised", source)
        self.assertIn("Axon-X sandbox health", source)
        self.assertIn("AXON_WATCH_CONTROL_PLANE_PORT", source)

        command = build_bwrap_command(
            ["axonhealth"],
            policy=policy,
            workspace_root=self.workspace,
            hook_material=material,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        path_index = command.index("PATH")
        self.assertTrue(command[path_index + 1].startswith("/run/axon-agent-policy/bin:"))
        self.assertNotIn(str(workspace_wrapper), command)

    def test_workspace_live_verify_is_materialized_not_resolved_from_workspace(self) -> None:
        workspace_wrapper = self.workspace / "bin" / "workspace-live-verify"
        workspace_wrapper.parent.mkdir(exist_ok=True)
        workspace_wrapper.write_text("#!/bin/sh\necho compromised\n", encoding="utf-8")
        workspace_wrapper.chmod(0o755)
        policy = self._policy(approved_wrappers=("workspace-live-verify",))

        with patch(
            "app.cli_runtime.agent_sandbox.shutil.which",
            return_value=str(workspace_wrapper),
        ):
            material = self._material(policy)

        wrapper = material.root / "bin" / "workspace-live-verify"
        self.assertTrue(wrapper.is_file())
        self.assertEqual(0o555, stat.S_IMODE(wrapper.stat().st_mode))
        source = wrapper.read_text(encoding="utf-8")
        self.assertNotIn(str(workspace_wrapper), source)
        self.assertNotIn("compromised", source)
        self.assertIn("/service-connection", source)
        self.assertIn("check-supabase", source)

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

    def test_codex_auth_file_mounts_only_into_private_codex_home(self) -> None:
        auth = self.temp_root / "profiles" / "codex" / "auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_text("{}", encoding="utf-8")
        policy = self._policy(codex_auth_path=str(auth))
        command = build_bwrap_command(
            ["/bin/true"],
            policy=policy,
            workspace_root=self.workspace,
            hook_material=self._material(policy),
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        destination = "/run/axon-agent-home/.codex/auth.json"
        self.assertIn(str(auth), command)
        self.assertIn(destination, command)

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

    @unittest.skipUnless(Path("/usr/bin/bwrap").is_file(), "Bubblewrap is unavailable")
    def test_linked_worktree_supports_read_only_git_status(self) -> None:
        repository = self.temp_root / "repository"
        linked = self.temp_root / "linked"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Axon Test"], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.email", "axon@example.invalid"], check=True)
        tracked = repository / "tracked.txt"
        tracked.write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repository), "add", "tracked.txt"], check=True)
        subprocess.run(["git", "-C", str(repository), "commit", "-qm", "base"], check=True)
        subprocess.run(["git", "-C", str(repository), "worktree", "add", "-q", "-b", "probe", str(linked)], check=True)
        (linked / ".axon-si").mkdir()
        tracked_linked = linked / "tracked.txt"
        tracked_linked.write_text("changed\n", encoding="utf-8")

        policy = self._policy(writable_roots=(".",), cursor_readonly_paths=())
        launch = wrap_command_in_agent_sandbox(
            ["/usr/bin/git", "status", "--short"],
            policy=policy,
            workspace_root=linked,
            run_id="run-linked-git-status",
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
        self.assertIn("tracked.txt", result.stdout)
        command = list(launch.command)
        common_git_dir = (repository / ".git").resolve()
        self.assertIn(str(common_git_dir), command)
        self.assertIn("/run/axon-agent-git/common", command)
        self.assertNotIn(str(common_git_dir / "worktrees" / "linked"), command)
        mount_destinations = [
            command[index + 2]
            for index, value in enumerate(command[:-2])
            if value in {"--ro-bind", "--bind"}
        ]
        self.assertNotIn(str(repository), mount_destinations)
        self.assertNotIn(str(common_git_dir), mount_destinations)
        self.assertIn(str(launch.hook_material.git_config), command)

    @unittest.skipUnless(Path("/usr/bin/bwrap").is_file(), "Bubblewrap is unavailable")
    def test_borrowed_node_modules_packages_are_readable_inside_bwrap(self) -> None:
        bound = self.temp_root / "bound"
        bound.mkdir()
        package = bound / "node_modules" / "pkg"
        package.mkdir(parents=True)
        (package / "marker.txt").write_text("borrowed\n", encoding="utf-8")

        modules = self.workspace / "node_modules"
        modules.mkdir()
        (modules / "pkg").symlink_to(package, target_is_directory=True)

        policy = self._policy(cursor_readonly_paths=())
        launch = wrap_command_in_agent_sandbox(
            [
                "/usr/bin/python3",
                "-c",
                "from pathlib import Path; print(Path('node_modules/pkg/marker.txt').read_text().strip())",
            ],
            policy=policy,
            workspace_root=self.workspace,
            run_id="run-borrowed-node-modules",
            policy_root=self.policy_root,
            bwrap_path="/usr/bin/bwrap",
            user_home=self.home,
        )
        command = list(launch.command)
        bind_targets = {
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--ro-bind"
        }
        self.assertIn(str((bound / "node_modules").resolve()), bind_targets)

        result = subprocess.run(
            launch.command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("borrowed", result.stdout.strip())


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

    def test_pre_tool_use_accepts_runtime_specific_event_casing(self) -> None:
        for event in ("preToolUse", "PreToolUse"):
            with self.subTest(event=event):
                self.assertEqual(
                    "allow",
                    self._evaluate("git status --short", event=event)["permission"],
                )

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
