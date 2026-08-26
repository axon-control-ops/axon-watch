from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_delivery.config import clear_config_cache_for_tests  # noqa: E402
from app.workspace_provisioning import (  # noqa: E402
    WorkspaceProvisioningError,
    WorkspaceProvisioningSpec,
    provision_workspace_project,
)


class WorkspaceProvisioningTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_config_cache_for_tests()

    def test_provisions_local_git_repo_and_delivery_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "move-it"
            delivery_file = Path(tempdir) / "workspace-delivery.json"
            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
                    "AXON_WATCH_WORKSPACE_DELIVERY_FILE": str(delivery_file),
                },
                clear=False,
            ):
                report = provision_workspace_project(
                    WorkspaceProvisioningSpec(
                        workspace_id="workspace_move_it",
                        project_root=root,
                        display_name="MoveIT",
                        github_repo="move-it",
                    )
                )

            self.assertEqual("ready", report["status"])
            self.assertTrue((root / ".git").is_dir())
            self.assertTrue((root / "project.axon.yaml").is_file())
            self.assertTrue((root / "package.json").is_file())
            self.assertTrue((root / "tests" / "smoke.test.js").is_file())
            self.assertTrue(os.access(root / "scripts" / "guardrails" / "check-workspace-health.sh", os.X_OK))

            npm = subprocess.run(
                ["npm", "test"],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, npm.returncode, npm.stderr + npm.stdout)

            head = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, head.returncode, head.stderr)

            payload = json.loads(delivery_file.read_text(encoding="utf-8"))
            policies = {
                item["workspace_id"]: item
                for item in payload["workspaces"]
                if isinstance(item, dict)
            }
            self.assertEqual("move-it", policies["workspace_move_it"]["github_repo"])
            self.assertEqual([], policies["workspace_move_it"]["workflow_names"])

    def test_rejects_github_owner_outside_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            with patch.dict(
                os.environ,
                {"AXON_WATCH_GITHUB_OWNER_ALLOWLIST": "axon-control-ops"},
                clear=False,
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "github_owner"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_demo",
                            project_root=Path(tempdir) / "demo",
                            github_owner="someone-else",
                            github_repo="demo",
                            create_github_repo=True,
                        )
                    )

    def test_rejects_project_root_outside_allowlist_before_creating_directory(self) -> None:
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as blocked:
            project_root = Path(blocked) / "demo"
            with patch.dict(
                os.environ,
                {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": allowed},
                clear=False,
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "outside allowlist"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_demo",
                            project_root=project_root,
                            github_repo="demo",
                        )
                    )
            self.assertFalse(project_root.exists())

    def test_github_creation_failure_is_reported_not_marked_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "demo"
            delivery_file = Path(tempdir) / "workspace-delivery.json"
            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
                    "AXON_WATCH_WORKSPACE_DELIVERY_FILE": str(delivery_file),
                },
                clear=False,
            ), patch(
                "app.workspace_provisioning.resolve_gh_cli",
                return_value="/bin/false",
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "github repo create failed"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_demo",
                            project_root=root,
                            github_repo="demo",
                            create_github_repo=True,
                        )
                    )
            self.assertFalse(delivery_file.exists())

    def test_existing_empty_github_repo_is_connected_and_pushed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "move-it"
            delivery_file = Path(tempdir) / "workspace-delivery.json"
            commands: list[list[str]] = []
            from app import workspace_provisioning

            real_run = workspace_provisioning._run

            def fake_run(args, *, cwd, timeout=60.0):
                command = [str(item) for item in args]
                commands.append(command)
                if command[:3] == ["/usr/bin/gh", "repo", "view"]:
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"name":"move-it"}\n', stderr="")
                if command[:3] == ["git", "push", "-u"]:
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout="pushed\n", stderr="")
                if command[:3] == ["git", "ls-remote", "origin"]:
                    head = real_run(["git", "rev-parse", "HEAD"], cwd=cwd)
                    return subprocess.CompletedProcess(
                        args=args,
                        returncode=0,
                        stdout=f"{head.stdout.strip()}\trefs/heads/main\n",
                        stderr="",
                    )
                return real_run(args, cwd=cwd, timeout=timeout)

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
                    "AXON_WATCH_WORKSPACE_DELIVERY_FILE": str(delivery_file),
                    "AXON_WATCH_GITHUB_OWNER_ALLOWLIST": "axon-control-ops",
                },
                clear=False,
            ), patch(
                "app.workspace_provisioning.resolve_gh_cli",
                return_value="/usr/bin/gh",
            ), patch(
                "app.workspace_provisioning._run",
                side_effect=fake_run,
            ):
                report = provision_workspace_project(
                    WorkspaceProvisioningSpec(
                        workspace_id="workspace_move_it",
                        project_root=root,
                        display_name="MoveIT",
                        github_repo="move-it",
                        create_github_repo=True,
                    )
                )

            self.assertEqual("ready", report["status"])
            self.assertEqual("present", report["github"]["status"])
            self.assertEqual("created", report["github"]["remote"]["status"])
            self.assertEqual(
                "https://github.com/axon-control-ops/move-it.git",
                report["github"]["remote"]["url"],
            )
            self.assertFalse(any(command[:3] == ["/usr/bin/gh", "repo", "create"] for command in commands))
            self.assertTrue(any(command[:3] == ["git", "remote", "add"] for command in commands))
            self.assertTrue(any(command[:3] == ["git", "push", "-u"] for command in commands))

    def test_starter_workspace_without_git_gets_safe_initial_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "starter"
            root.mkdir()
            (root / "README.md").write_text("# Starter\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=must-not-stage\n", encoding="utf-8")
            (root / ".axon_terminal_history_terminal-operator").write_text("token-ish\n", encoding="utf-8")
            delivery_file = Path(tempdir) / "workspace-delivery.json"

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
                    "AXON_WATCH_WORKSPACE_DELIVERY_FILE": str(delivery_file),
                },
                clear=False,
            ):
                report = provision_workspace_project(
                    WorkspaceProvisioningSpec(
                        workspace_id="workspace_starter",
                        project_root=root,
                        scaffold_files=False,
                        enable_delivery=False,
                    )
                )

            self.assertEqual("ready", report["status"])
            committed = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertEqual(["README.md"], [line for line in committed if line.strip()])

    def test_empty_workspace_without_safe_files_reports_actionable_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "empty"
            root.mkdir()
            with patch.dict(
                os.environ,
                {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir},
                clear=False,
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "no safe starter files"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_empty",
                            project_root=root,
                            scaffold_files=False,
                            enable_delivery=False,
                        )
                    )

    def test_wrong_existing_origin_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "wrong-origin"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Axon Test"], cwd=root, check=True)
            (root / "README.md").write_text("# Wrong\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", "https://github.com/other/repo.git"], cwd=root, check=True)

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
                    "AXON_WATCH_GITHUB_OWNER_ALLOWLIST": "axon-control-ops",
                },
                clear=False,
            ), patch(
                "app.workspace_provisioning.resolve_gh_cli",
                return_value="/usr/bin/gh",
            ), patch(
                "app.workspace_provisioning._run",
                side_effect=lambda args, *, cwd, timeout=60.0: (
                    subprocess.CompletedProcess(args=args, returncode=0, stdout='{"name":"move-it"}\n', stderr="")
                    if [str(item) for item in args][:3] == ["/usr/bin/gh", "repo", "view"]
                    else subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout)
                ),
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "refusing to overwrite"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_wrong_origin",
                            project_root=root,
                            github_repo="move-it",
                            create_github_repo=True,
                            scaffold_files=False,
                            enable_delivery=False,
                        )
                    )

    def test_push_failure_is_not_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "push-failure"
            root.mkdir()
            delivery_file = Path(tempdir) / "workspace-delivery.json"

            def fake_run(args, *, cwd, timeout=60.0):
                command = [str(item) for item in args]
                if command[:3] == ["/usr/bin/gh", "repo", "view"]:
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"name":"move-it"}\n', stderr="")
                if command[:3] == ["git", "push", "-u"]:
                    return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="denied")
                return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout)

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir,
                    "AXON_WATCH_WORKSPACE_DELIVERY_FILE": str(delivery_file),
                },
                clear=False,
            ), patch("app.workspace_provisioning.resolve_gh_cli", return_value="/usr/bin/gh"), patch(
                "app.workspace_provisioning._run",
                side_effect=fake_run,
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "git push failed"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_push_fail",
                            project_root=root,
                            github_repo="move-it",
                            create_github_repo=True,
                        )
                    )
            self.assertFalse(delivery_file.exists())

    def test_remote_sha_must_match_local_head(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "remote-mismatch"
            root.mkdir()

            def fake_run(args, *, cwd, timeout=60.0):
                command = [str(item) for item in args]
                if command[:3] == ["/usr/bin/gh", "repo", "view"]:
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"name":"move-it"}\n', stderr="")
                if command[:3] == ["git", "push", "-u"]:
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout="pushed\n", stderr="")
                if command[:3] == ["git", "ls-remote", "origin"]:
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout="deadbeef\trefs/heads/main\n", stderr="")
                return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout)

            with patch.dict(
                os.environ,
                {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": tempdir},
                clear=False,
            ), patch("app.workspace_provisioning.resolve_gh_cli", return_value="/usr/bin/gh"), patch(
                "app.workspace_provisioning._run",
                side_effect=fake_run,
            ):
                with self.assertRaisesRegex(WorkspaceProvisioningError, "remote main=deadbeef"):
                    provision_workspace_project(
                        WorkspaceProvisioningSpec(
                            workspace_id="workspace_remote_mismatch",
                            project_root=root,
                            github_repo="move-it",
                            create_github_repo=True,
                        )
                    )


if __name__ == "__main__":
    unittest.main()
