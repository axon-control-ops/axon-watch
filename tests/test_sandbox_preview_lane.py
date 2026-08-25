"""Sandbox preview lane: cwd targeting and preview-command selection."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.workspace_delivery.publish import list_isolation_changed_paths
from app.cli_runtime.composer_sandbox import _changed_paths

from app.cli_runtime import sandbox_preview
from app.cli_runtime.sandbox_preview import (
    SandboxPreviewError,
    ensure_isolation_checkout_runnable,
    ensure_preview_dependencies,
    ensure_preview_env_files,
    ensure_sandbox_checkout_runnable,
    sandbox_preview_command,
    start_sandbox_preview,
)
from app.terminal.agent_jobs import TARGET_SANDBOX, TARGET_WORKSPACE, _resolve_job_root


class SandboxPreviewCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _package(self, payload: dict[str, object]) -> None:
        (self.root / "package.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_expo_preview_always_clears_the_metro_cache(self) -> None:
        # Metro inlines EXPO_PUBLIC_* at transform time and caches by file
        # content. A checkout's first preview runs before env files are linked,
        # baking `undefined` in permanently — restarts do not invalidate it.
        self._package(
            {"scripts": {"web:dev": "expo start --web"}, "dependencies": {"expo": "^51"}}
        )
        self.assertIn("--clear", sandbox_preview_command(self.root, 8083))

    def test_expo_web_prefers_the_local_bin_over_npx(self) -> None:
        # `npx --no-install expo` resolves the *package* and cancels when
        # node_modules is a borrowed symlink; the bin shim is what exists.
        self._package(
            {"scripts": {"web:dev": "expo start --web"}, "dependencies": {"expo": "^51"}}
        )
        binary = self.root / "node_modules" / ".bin" / "expo"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        self.assertEqual(
            sandbox_preview_command(self.root, 8083),
            "./node_modules/.bin/expo start --web --port 8083 --clear",
        )

    def test_expo_web_falls_back_to_npx_without_a_local_bin(self) -> None:
        self._package(
            {"scripts": {"web:dev": "expo start --web"}, "dependencies": {"expo": "^51"}}
        )
        self.assertEqual(
            sandbox_preview_command(self.root, 8083),
            "npx --no-install expo start --web --port 8083 --clear",
        )

    def test_vite_dev_script_receives_a_forwarded_port_flag(self) -> None:
        self._package({"scripts": {"dev": "vite"}})
        self.assertEqual(sandbox_preview_command(self.root, 8084), "npm run dev -- --port 8084")

    def test_unrecognised_dev_entrypoint_uses_the_port_env_var_only(self) -> None:
        # Forwarding --port to a shell-script entrypoint would just crash it.
        self._package({"scripts": {"dev": "./scripts/dev/up.sh"}})
        self.assertEqual(sandbox_preview_command(self.root, 8084), "PORT=8084 npm run dev")

    def test_command_never_prefixes_cd(self) -> None:
        # The PTY job is spawned with the checkout as cwd; a `cd` would be a
        # second place for the path to drift.
        self._package({"scripts": {"dev": "vite"}})
        self.assertNotIn("cd ", sandbox_preview_command(self.root, 8083))

    def test_missing_preview_script_is_an_explicit_error(self) -> None:
        self._package({"scripts": {"build": "tsc"}})
        with self.assertRaises(SandboxPreviewError):
            sandbox_preview_command(self.root, 8083)


class SandboxCheckoutIsolationGapTests(unittest.TestCase):
    """A worktree only contains tracked files, so a preview must supply the rest."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.checkout = base / "checkout"
        self.bound = base / "bound"
        self.checkout.mkdir()
        self.bound.mkdir()

    def test_empty_node_modules_is_populated_with_per_package_links(self) -> None:
        # The real failure: npm leaves an empty dir, so an existence check alone
        # would conclude dependencies were present and start an unrunnable app.
        (self.checkout / "node_modules").mkdir()
        (self.bound / "node_modules" / "expo").mkdir(parents=True)
        ensure_preview_dependencies(self.checkout, self.bound)
        modules = self.checkout / "node_modules"
        self.assertTrue((modules / "expo").is_dir())
        # node_modules must stay a real directory resolving inside the checkout:
        # it is an approved writable root, and the agent sandbox rejects any
        # writable root that escapes the disposable workspace. Linking the whole
        # tree failed every Lane B dispatch.
        self.assertFalse(modules.is_symlink())
        self.assertTrue(modules.resolve().is_relative_to(self.checkout.resolve()))

    def test_a_stale_whole_tree_symlink_is_replaced(self) -> None:
        # Checkouts bootstrapped by the earlier build of this lane carry the
        # escaping link that broke dispatch; starting a preview must heal it.
        (self.bound / "node_modules" / "expo").mkdir(parents=True)
        (self.checkout / "node_modules").symlink_to(
            self.bound / "node_modules", target_is_directory=True
        )
        ensure_preview_dependencies(self.checkout, self.bound)
        self.assertFalse((self.checkout / "node_modules").is_symlink())
        self.assertTrue((self.checkout / "node_modules" / "expo").is_dir())

    def test_populated_checkout_dependencies_are_left_alone(self) -> None:
        (self.checkout / "node_modules" / "already").mkdir(parents=True)
        (self.bound / "node_modules" / "other").mkdir(parents=True)
        ensure_preview_dependencies(self.checkout, self.bound)
        self.assertFalse((self.checkout / "node_modules").is_symlink())
        self.assertTrue((self.checkout / "node_modules" / "other").is_dir())

    def test_partial_checkout_dependencies_receive_missing_packages(self) -> None:
        (self.checkout / "node_modules" / ".cache").mkdir(parents=True)
        (self.bound / "node_modules" / "jest").mkdir(parents=True)
        ensure_preview_dependencies(self.checkout, self.bound)
        self.assertTrue((self.checkout / "node_modules" / "jest").is_dir())

    def test_workspace_scripts_receive_root_bin_shims(self) -> None:
        (self.checkout / "package.json").write_text(
            json.dumps({"workspaces": ["apps/*"]}),
            encoding="utf-8",
        )
        (self.checkout / "apps" / "console-web").mkdir(parents=True)
        (self.checkout / "apps" / "console-web" / "package.json").write_text(
            json.dumps({"scripts": {"test": "vitest run"}}),
            encoding="utf-8",
        )
        (self.bound / "node_modules" / ".bin").mkdir(parents=True)
        (self.bound / "node_modules" / "vitest").mkdir(parents=True)
        (self.bound / "node_modules" / "vitest" / "vitest.mjs").write_text(
            "#!/usr/bin/env node\n",
            encoding="utf-8",
        )
        (self.bound / "node_modules" / ".bin" / "vitest").symlink_to(
            "../vitest/vitest.mjs"
        )

        ensure_preview_dependencies(self.checkout, self.bound)

        root_bin = self.checkout / "node_modules" / ".bin"
        app_bin = self.checkout / "apps" / "console-web" / "node_modules" / ".bin"
        self.assertFalse(root_bin.is_symlink())
        self.assertTrue((root_bin / "vitest").is_symlink())
        self.assertTrue((app_bin / "vitest").is_symlink())
        self.assertTrue((app_bin / "vitest").exists())
        self.assertIn("node_modules/.bin/vitest", os.readlink(app_bin / "vitest"))

    def test_stale_root_bin_symlink_is_replaced_with_real_directory(self) -> None:
        (self.bound / "node_modules" / ".bin").mkdir(parents=True)
        (self.bound / "node_modules" / ".bin" / "vitest").write_text(
            "#!/bin/sh\n",
            encoding="utf-8",
        )
        (self.checkout / "node_modules").mkdir()
        (self.checkout / "node_modules" / ".bin").symlink_to(
            self.bound / "node_modules" / ".bin",
            target_is_directory=True,
        )

        ensure_preview_dependencies(self.checkout, self.bound)

        checkout_bin = self.checkout / "node_modules" / ".bin"
        self.assertTrue(checkout_bin.is_dir())
        self.assertFalse(checkout_bin.is_symlink())
        self.assertTrue((checkout_bin / "vitest").exists())

    def test_missing_dependencies_everywhere_is_an_actionable_error(self) -> None:
        with self.assertRaises(SandboxPreviewError) as caught:
            ensure_preview_dependencies(self.checkout, self.bound)
        self.assertIn("dependencies", str(caught.exception))

    def test_gitignored_env_files_are_copied_but_example_is_not_shadowed(self) -> None:
        for name in (".env", ".env.local", ".env.example"):
            (self.bound / name).write_text("A=1\n", encoding="utf-8")
        (self.checkout / ".env.example").write_text("A=\n", encoding="utf-8")
        linked = ensure_preview_env_files(self.checkout, self.bound)
        self.assertEqual(linked, [".env", ".env.local"])
        self.assertFalse((self.checkout / ".env").is_symlink())
        self.assertEqual((self.checkout / ".env").read_text(encoding="utf-8"), "A=1\n")
        # The tracked example already exists in the worktree; never replace it.

    def test_stale_env_symlinks_are_replaced_with_copies(self) -> None:
        (self.bound / "node_modules" / "jest").mkdir(parents=True)
        (self.bound / ".env.production").write_text("PROD=1\n", encoding="utf-8")
        (self.checkout / ".env.production").symlink_to(self.bound / ".env.production")
        result = ensure_sandbox_checkout_runnable(self.checkout, self.bound)
        self.assertTrue(result["ok"])
        self.assertFalse((self.checkout / ".env.production").is_symlink())
        self.assertEqual(
            (self.checkout / ".env.production").read_text(encoding="utf-8"),
            "PROD=1\n",
        )

    def test_isolation_bootstrap_reads_bound_root_from_sidecar(self) -> None:
        (self.bound / "node_modules" / "jest").mkdir(parents=True)
        sidecar = self.checkout / ".axon-si"
        sidecar.mkdir()
        (sidecar / "baseline.json").write_text(
            json.dumps({"bound_project_root": str(self.bound)}),
            encoding="utf-8",
        )
        result = ensure_isolation_checkout_runnable(self.checkout)
        self.assertTrue(result["ok"])
        self.assertTrue((self.checkout / "node_modules" / "jest").is_dir())
        self.assertFalse((self.checkout / ".env.example").is_symlink())

    def test_env_linking_never_overwrites_a_checkout_file(self) -> None:
        (self.bound / ".env").write_text("FROM=bound\n", encoding="utf-8")
        (self.checkout / ".env").write_text("FROM=checkout\n", encoding="utf-8")
        self.assertEqual(ensure_preview_env_files(self.checkout, self.bound), [])
        self.assertEqual((self.checkout / ".env").read_text(encoding="utf-8"), "FROM=checkout\n")

    def test_untracked_document_assets_are_borrowed_from_bound_root(self) -> None:
        (self.bound / "docs" / "rfq").mkdir(parents=True)
        (self.bound / "docs" / "rfq" / "filled.pdf").write_bytes(b"%PDF-1.4")
        (self.checkout / "docs" / "rfq").mkdir(parents=True)
        (self.checkout / "docs" / "rfq" / "tracked.txt").write_text("old\n", encoding="utf-8")
        result = ensure_sandbox_checkout_runnable(self.checkout, self.bound)
        self.assertTrue(result["ok"])
        self.assertTrue((self.checkout / "docs" / "rfq" / "filled.pdf").is_file())
        self.assertIn("borrowed document assets", " ".join(result["notes"]))


class PreviewBootstrapMustNotPolluteChangesTests(unittest.TestCase):
    """Bootstrap symlinks must never reach Review or Publish.

    node_modules is not gitignored in every project, so the borrowed link shows
    up as an untracked change. Publishing that would write a symlink pointing
    into /tmp onto the bound project root.
    """

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.checkout = Path(self.temp.name) / "checkout"
        self.outside = Path(self.temp.name) / "outside"
        self.checkout.mkdir()
        (self.outside / "pkg").mkdir(parents=True)
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@example.com"],
            ["git", "config", "user.name", "T"],
        ):
            subprocess.run(args, cwd=self.checkout, check=True)
        (self.checkout / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.checkout, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=self.checkout, check=True)

    def _changed(self) -> list[str]:
        # _changed_paths gates on isolation sidecar metadata a bare temp repo
        # has no reason to carry; the behaviour under test is the filtering.
        with patch("app.cli_runtime.composer_sandbox._root_valid", return_value=True):
            return _changed_paths(self.checkout)

    def test_escaping_symlink_is_filtered_but_real_edits_survive(self) -> None:
        (self.checkout / "node_modules").symlink_to(self.outside, target_is_directory=True)
        (self.checkout / "authored.ts").write_text("export const a = 1;\n", encoding="utf-8")

        # Borrowed links are filtered at the shared chokepoint, so delivery's
        # diff budget never counts them either. Before that fix they reached
        # Gate 6 as 1012 changed paths and blocked every delivery.
        self.assertNotIn("node_modules", list_isolation_changed_paths(self.checkout))

        filtered = self._changed()
        self.assertNotIn("node_modules", filtered)
        self.assertIn("authored.ts", filtered)

    def test_symlink_inside_the_checkout_is_still_a_real_change(self) -> None:
        # Only *escaping* links are infrastructure; an in-tree symlink is content.
        (self.checkout / "alias.txt").symlink_to(self.checkout / "seed.txt")
        self.assertIn("alias.txt", self._changed())


class PreviewProcessControlTests(unittest.TestCase):
    """Listing and stopping preview servers, including orphans."""

    def setUp(self) -> None:
        sandbox_preview.reset_sandbox_previews()
        self.addCleanup(sandbox_preview.reset_sandbox_previews)

    def test_stop_refuses_ports_outside_the_preview_range(self) -> None:
        # This endpoint is reachable over HTTP; without the range guard it would
        # be a general-purpose process killer.
        for port in (22, 5173, 8080, 8082, 9000):
            with self.assertRaises(SandboxPreviewError) as caught:
                sandbox_preview.stop_preview_port("workspace_demo", port)
            self.assertIn("outside the preview range", str(caught.exception))

    def test_stop_does_not_signal_anything_when_the_port_is_idle(self) -> None:
        with patch.object(sandbox_preview, "_listening_processes", return_value={}), patch(
            "os.kill"
        ) as killed:
            result = sandbox_preview.stop_preview_port("workspace_demo", 8083)
        killed.assert_not_called()
        self.assertFalse(result["stopped"])

    def test_stop_signals_the_listener_on_an_in_range_port(self) -> None:
        with patch.object(
            sandbox_preview, "_listening_processes", return_value={8084: (4321, "node")}
        ), patch("os.kill") as killed:
            result = sandbox_preview.stop_preview_port("workspace_demo", 8084)
        killed.assert_called_once()
        self.assertEqual(killed.call_args.args[0], 4321)
        self.assertTrue(result["stopped"])

    def test_discovery_reports_untracked_servers_as_orphans(self) -> None:
        # A preview outliving a control-plane restart must still be reclaimable.
        with patch.object(
            sandbox_preview, "_listening_processes", return_value={8086: (777, "node")}
        ):
            listing = sandbox_preview.discover_previews("workspace_demo")
        self.assertEqual(listing["count"], 1)
        self.assertFalse(listing["items"][0]["managed"])
        self.assertEqual(listing["items"][0]["url"], "http://localhost:8086")


class SandboxJobTargetTests(unittest.TestCase):
    def test_sandbox_target_refuses_to_fall_back_to_the_bound_root(self) -> None:
        # The whole point of the target is that a preview never silently serves
        # the bound project root while the operator reads it as sandbox-only.
        with patch(
            "app.cli_runtime.composer_sandbox.resolve_sandbox_workspace_root",
            return_value=None,
        ):
            with self.assertRaises(ValueError) as caught:
                _resolve_job_root("workspace_demo", TARGET_SANDBOX)
        self.assertIn("sandbox", str(caught.exception))

    def test_workspace_target_resolves_the_bound_root(self) -> None:
        with patch(
            "app.terminal.agent_jobs.resolve_workspace_root",
            return_value=Path("/tmp/bound"),
        ):
            self.assertEqual(_resolve_job_root("workspace_demo", TARGET_WORKSPACE), Path("/tmp/bound"))

    def test_start_preview_enqueues_on_the_sandbox_target(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8")
        sandbox_preview.reset_sandbox_previews()
        self.addCleanup(sandbox_preview.reset_sandbox_previews)

        bound = Path(temp.name).parent / "bound-root"
        (bound / "node_modules" / "pkg").mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(bound, ignore_errors=True))

        with patch(
            "app.cli_runtime.composer_sandbox.resolve_sandbox_workspace_root",
            return_value=root,
        ), patch(
            "app.terminal.workspace_roots.resolve_workspace_root",
            return_value=bound,
        ), patch(
            "app.cli_runtime.sandbox_preview.enqueue_agent_terminal_job",
            return_value={"job_id": "agent-job-test", "status": "running"},
        ) as enqueue:
            result = start_sandbox_preview("workspace_demo")

        kwargs = enqueue.call_args.kwargs
        self.assertEqual(kwargs["target"], TARGET_SANDBOX)
        self.assertFalse(kwargs["stream_to_chat"])
        # Assert the service classification, not a requested timeout value: the
        # batch ceiling silently clamps any large timeout_seconds to one hour,
        # so asserting the request proves nothing about the real deadline.
        self.assertTrue(kwargs["service"])
        self.assertTrue(result["running"])
        self.assertEqual(result["checkout_root"], str(root))
        self.assertIn(result["port"], sandbox_preview.PREVIEW_PORT_RANGE)
        self.assertEqual(result["url"], f"http://localhost:{result['port']}")


if __name__ == "__main__":
    unittest.main()
