from __future__ import annotations

import unittest

from scripts.verify.check_constitution_gates import run_check


class ConstitutionGateScriptTests(unittest.TestCase):
    def test_constitution_gate_passes_current_registry_spine(self) -> None:
        results = run_check()

        failed = [result for result in results if result.status == "fail"]
        self.assertEqual([], failed)
        names = {result.name for result in results}
        self.assertIn("constitution_registry_tables", names)
        self.assertIn("mutating_methods_guarded", names)
        self.assertIn("constitution_handoff_ledger", names)


if __name__ == "__main__":
    unittest.main()
