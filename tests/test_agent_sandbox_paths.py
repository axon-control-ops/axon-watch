from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.agent_sandbox_paths import (  # noqa: E402
    append_outside_symlink_binds,
    workspace_outside_symlink_mounts,
)


class AgentSandboxPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.checkout = base / "checkout"
        self.bound = base / "bound"
        self.checkout.mkdir()
        self.bound.mkdir()

    def test_per_package_node_modules_symlinks_are_discovered(self) -> None:
        (self.bound / "node_modules" / "jest").mkdir(parents=True)
        modules = self.checkout / "node_modules"
        modules.mkdir()
        (modules / "jest").symlink_to(self.bound / "node_modules" / "jest", target_is_directory=True)

        mounts = workspace_outside_symlink_mounts(self.checkout)
        self.assertEqual(len(mounts), 1)
        target, link = mounts[0]
        self.assertEqual(target, (self.bound / "node_modules").resolve())
        self.assertEqual(link, modules)

    def test_whole_tree_node_modules_symlink_is_discovered(self) -> None:
        bound_modules = self.bound / "node_modules"
        bound_modules.mkdir(parents=True)
        (bound_modules / "pkg").mkdir()
        modules = self.checkout / "node_modules"
        modules.symlink_to(bound_modules, target_is_directory=True)

        mounts = workspace_outside_symlink_mounts(self.checkout)
        self.assertEqual(len(mounts), 1)
        self.assertEqual(mounts[0][1], modules)

    def test_append_outside_symlink_binds_emits_ro_bind_pairs(self) -> None:
        (self.bound / "node_modules" / "pkg").mkdir(parents=True)
        modules = self.checkout / "node_modules"
        modules.mkdir()
        (modules / "pkg").symlink_to(self.bound / "node_modules" / "pkg", target_is_directory=True)

        arguments: list[str] = []
        append_outside_symlink_binds(arguments, self.checkout)
        self.assertIn("--ro-bind", arguments)
        bind_index = arguments.index("--ro-bind")
        self.assertEqual(arguments[bind_index + 1], str((self.bound / "node_modules").resolve()))
        self.assertEqual(arguments[bind_index + 2], str(modules))


if __name__ == "__main__":
    unittest.main()
