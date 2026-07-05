"""Cross-repo planning migration verification."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNING_DIR = REPO_ROOT / "docs" / "planning"
MANIFEST_FILE = PLANNING_DIR / "MANIFEST.json"
REQUIRED_DOCS = (
    "PARITY_LEDGER.md",
    "IMPORT_MATRIX.md",
    "IMPLEMENTATION_ROADMAP.md",
    "PRODUCT.md",
    "ARCHITECTURE.md",
    "UI_SPEC.md",
)


class PlanningBundleMigrationTests(unittest.TestCase):
    def test_planning_directory_exists(self) -> None:
        self.assertTrue(PLANNING_DIR.is_dir())

    def test_required_planning_docs_present(self) -> None:
        for name in REQUIRED_DOCS:
            with self.subTest(name=name):
                self.assertTrue((PLANNING_DIR / name).is_file())

    def test_manifest_lists_all_markdown_files(self) -> None:
        payload = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        recorded = set(payload["files"].keys())
        current = {
            path.name
            for path in PLANNING_DIR.iterdir()
            if path.is_file() and path.suffix == ".md"
        }
        self.assertEqual(recorded, current)

    def test_manifest_validate_script_passes(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/ops/planning_bundle_manifest.py", "validate"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            msg=result.stderr or result.stdout,
        )

    def test_readme_declares_canonical_home(self) -> None:
        readme = (PLANNING_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Canonical home", readme)
        self.assertIn("docs/planning/", readme)

    def test_migration_spec_exists(self) -> None:
        spec = REPO_ROOT / "docs" / "CROSS_REPO_PLANNING_MIGRATION.md"
        self.assertTrue(spec.is_file())


if __name__ == "__main__":
    unittest.main()
