"""CLI binary discovery for the runtime catalog.

Regression coverage: find_cursor_cli used to resolve to the "cursor"
IDE-launcher shim, which internally re-execs a *separate* "agent" symlink at
runtime (`exec "$HOME/.local/bin/agent" "$@"`). That indirection is invisible
to the process sandbox — it only bind-mounts the resolved binary's own
directory, not a second hop the binary jumps to on its own — so every
sandboxed Cursor dispatch ran the shim against a symlink target that was
never exposed to the sandbox, surfacing as a spurious "Could not install
cursor-agent" failure even on a real, working install. Preferring
"cursor-agent" directly avoids the shim's opaque indirection entirely.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.catalog_discovery import (  # noqa: E402
    cli_runtime_family,
    find_cursor_cli,
)


def _make_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class CliRuntimeFamilyTests(unittest.TestCase):
    def test_recognizes_cursor_agent_binary_as_cursor_family(self) -> None:
        self.assertEqual("cursor", cli_runtime_family("/home/edp/.local/bin/cursor-agent"))
        self.assertEqual("cursor", cli_runtime_family("/home/edp/.local/bin/cursor"))


class FindCursorCliTests(unittest.TestCase):
    def test_prefers_cursor_agent_binary_over_cursor_shim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            bin_dir = home / ".local" / "bin"
            bin_dir.mkdir(parents=True)
            _make_executable(bin_dir / "cursor")
            _make_executable(bin_dir / "cursor-agent")
            with patch.dict(os.environ, {"HOME": str(home), "PATH": ""}, clear=False):
                found = find_cursor_cli()
        self.assertEqual(str(bin_dir / "cursor-agent"), found)

    def test_falls_back_to_cursor_shim_when_cursor_agent_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            bin_dir = home / ".local" / "bin"
            bin_dir.mkdir(parents=True)
            _make_executable(bin_dir / "cursor")
            with patch.dict(os.environ, {"HOME": str(home), "PATH": ""}, clear=False):
                found = find_cursor_cli()
        self.assertEqual(str(bin_dir / "cursor"), found)

    def test_override_path_still_wins_when_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            override = bin_dir / "cursor-agent"
            _make_executable(override)
            found = find_cursor_cli(str(override))
        self.assertEqual(str(override), found)


if __name__ == "__main__":
    unittest.main()
