from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from scripts.guardrails import common


ROOT = Path(__file__).resolve().parents[1]


class GuardrailCommonTests(unittest.TestCase):
    def test_ratcheted_file_budget_detects_growth_and_stale_manifest(self):
        self.assertIsNone(common.evaluate_ratcheted_file("main.py", 10, 10))
        self.assertIn(
            "exceeds ratchet budget 10",
            common.evaluate_ratcheted_file("main.py", 11, 10) or "",
        )
        self.assertIsNone(common.evaluate_ratcheted_file("main.py", 9, 10))
        self.assertIn(
            "lower the manifest to 50",
            common.evaluate_ratcheted_file("main.py", 50, 200) or "",
        )

    def test_load_budget_manifest_has_hotspots(self):
        manifest = common.load_budget_manifest(ROOT)
        self.assertIn("critical_hotspots", manifest)
        self.assertIn("ratcheted_oversize_files", manifest)
        self.assertIn(
            "apps/console-web/src/api/control-plane.ts",
            manifest["ratcheted_oversize_files"],
        )


class GuardrailScriptTests(unittest.TestCase):
    def test_check_file_sizes_passes_on_repo_baseline(self):
        result = subprocess.run(
            ["python3", "scripts/guardrails/check_file_sizes.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=result.stdout + result.stderr,
        )
        self.assertIn("File-size guardrails passed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
