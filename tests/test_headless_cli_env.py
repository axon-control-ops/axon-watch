from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.subprocess_runner import (  # noqa: E402
    communicate_registered_process,
    headless_cli_env,
    stream_registered_process,
)


class HeadlessCliEnvTests(unittest.TestCase):
    def test_sets_term_when_missing(self) -> None:
        env = headless_cli_env({"PATH": "/usr/bin", "HOME": "/tmp"})
        self.assertEqual(env["TERM"], "xterm-256color")
        self.assertEqual(env["COLORTERM"], "truecolor")
        self.assertEqual(env["NO_COLOR"], "1")
        self.assertTrue(env["PATH"].startswith("/usr/bin"))

    def test_adds_user_local_bin_when_available(self) -> None:
        with (
            patch("app.cli_runtime.user_bin_path.Path.is_dir", return_value=True),
            patch("app.cli_runtime.user_bin_path.Path.exists", return_value=True),
        ):
            env = headless_cli_env({"PATH": "/usr/bin", "HOME": "/tmp"})

        self.assertIn("/home/vaxon/.local/bin", env["PATH"].split(":"))

    def test_preserves_existing_term(self) -> None:
        env = headless_cli_env({"TERM": "screen-256color", "COLORTERM": "yes"})
        self.assertEqual(env["TERM"], "screen-256color")
        self.assertEqual(env["COLORTERM"], "yes")
        self.assertEqual(env["NO_COLOR"], "1")

    def test_blank_term_is_treated_as_missing(self) -> None:
        env = headless_cli_env({"TERM": "  ", "COLORTERM": ""})
        self.assertEqual(env["TERM"], "xterm-256color")
        self.assertEqual(env["COLORTERM"], "truecolor")

    def test_communicate_passes_term_into_popen(self) -> None:
        captured: dict[str, object] = {}

        class FakeProc:
            returncode = 0

            def communicate(self, timeout=None):  # noqa: ANN001
                return "ok", ""

        def fake_popen(*args, **kwargs):  # noqa: ANN001
            captured["env"] = kwargs.get("env")
            return FakeProc()

        with (
            patch("app.cli_runtime.subprocess_runner.subprocess.Popen", side_effect=fake_popen),
            patch("app.cli_runtime.subprocess_runner.wrap_command_in_agent_scope", side_effect=lambda cmd: cmd),
            patch("app.cli_runtime.subprocess_runner.register"),
            patch("app.cli_runtime.subprocess_runner.unregister"),
        ):
            stdout, stderr, code = communicate_registered_process(
                run_id="run_term",
                command=["cursor-agent", "--print", "hi"],
                timeout_seconds=5,
                subprocess_env={"PATH": "/usr/bin"},
            )

        self.assertEqual(stdout, "ok")
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)
        env = captured["env"]
        assert isinstance(env, dict)
        self.assertEqual(env["TERM"], "xterm-256color")
        self.assertEqual(env["NO_COLOR"], "1")

    def test_stream_closes_process_pipes(self) -> None:
        stdout, stderr, code = stream_registered_process(
            run_id="run_stream_cleanup",
            command=[sys.executable, "-c", "print('ready')"],
            timeout_seconds=5,
        )

        self.assertEqual(stdout, "ready\n")
        self.assertEqual(stderr, "")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
