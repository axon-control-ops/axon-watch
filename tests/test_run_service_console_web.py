"""Contract: always-on console-web must proxy /api via vite preview."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SERVICE = REPO_ROOT / "scripts" / "ops" / "run-service.sh"


class RunServiceConsoleWebContractTests(unittest.TestCase):
    def test_console_web_prefers_vite_preview_over_http_server(self) -> None:
        script = RUN_SERVICE.read_text(encoding="utf-8")
        console_case = script.split("console-web)", 1)[1].split("*)", 1)[0]
        self.assertIn("vite", console_case)
        self.assertIn("preview", console_case)
        self.assertIn('if [[ ! -d dist ]]', console_case)
        self.assertIn('AXON_WATCH_CONSOLE_STATIC_ONLY:-0', console_case)
        # Executable http.server is opt-in only (ignore comment mentions).
        static_only_index = console_case.index("AXON_WATCH_CONSOLE_STATIC_ONLY")
        http_server_exec = console_case.index("-m http.server")
        self.assertLess(static_only_index, http_server_exec)
        self.assertGreater(console_case.rindex("preview"), http_server_exec)


if __name__ == "__main__":
    unittest.main()
