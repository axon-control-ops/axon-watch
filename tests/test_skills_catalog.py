from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.skills_catalog import build_skills_snapshot  # noqa: E402


class SkillsCatalogTests(unittest.TestCase):
    def test_lists_skills_from_bound_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "project"
            skill_dir = project_root / ".github" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: Demo playbook\n---\n\nBody\n",
                encoding="utf-8",
            )
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_demo": {
                                "project_root": str(project_root),
                                "display_name": "Demo",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                },
                clear=False,
            ):
                snapshot = build_skills_snapshot()

            self.assertEqual(snapshot["count"], 1)
            item = snapshot["items"][0]
            assert isinstance(item, dict)
            self.assertEqual(item["name"], "demo-skill")
            self.assertEqual(item["workspace_id"], "workspace_demo")
            self.assertEqual(item["path"], ".github/skills/demo-skill/SKILL.md")


if __name__ == "__main__":
    unittest.main()
