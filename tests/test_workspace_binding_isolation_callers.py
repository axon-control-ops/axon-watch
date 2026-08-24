"""Every full-registry scan of workspace bindings must survive one bad entry.

Regression guard, round 3, of the same root cause. get_workspace_record and
list_workspace_records were fixed for it directly (see
test_workspace_project_bindings.py). A repo-wide search for
load_workspace_project_bindings turned up seven more call sites -- every one
of them a best-effort scan across all workspaces (briefing display names,
project-root reverse lookup, agent record listing, chat/kairo alias matching,
skills catalog discovery), none of them the one caller that legitimately needs
the strict, fail-closed "trust every binding" contract
(test_rejects_project_root_outside_allowlist covers that one directly). Each
was migrated to list_valid_workspace_project_bindings, which skips a bad entry
instead of failing the whole scan. This test proves each migrated call site
resolves the *good* workspace correctly despite an unrelated *bad* one sitting
right next to it in the same bindings file.
"""

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


class WorkspaceBindingIsolationCallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.good_root = base / "good"
        self.good_root.mkdir()
        self.bad_root = base / "bad"
        self.bad_root.mkdir()
        self.bindings_file = base / "bindings.json"
        self.bindings_file.write_text(
            json.dumps(
                {
                    "bindings": {
                        "workspace_good": {
                            "project_root": str(self.good_root),
                            "display_name": "Good Co",
                        },
                        "workspace_bad": {"project_root": str(self.bad_root)},
                    }
                }
            ),
            encoding="utf-8",
        )
        self._env_patch = patch.dict(
            os.environ,
            {"AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(self.good_root)},
            clear=False,
        )
        self._file_patch = patch(
            "app.workspace_project_bindings.default_bindings_file",
            return_value=self.bindings_file,
        )
        self._env_patch.start()
        self._file_patch.start()
        self.addCleanup(self._env_patch.stop)
        self.addCleanup(self._file_patch.stop)

    def test_workspace_service_connections_reverse_lookup_survives(self) -> None:
        from app.workspace_service_connections import workspace_id_for_project_root

        self.assertEqual("workspace_good", workspace_id_for_project_root(self.good_root))

    def test_agent_records_listing_survives(self) -> None:
        from app.workspace_agents import list_workspace_agent_records

        records = list_workspace_agent_records()
        self.assertIsInstance(records, list)
        ids = {str(r.get("workspace_id") or "") for r in records}
        self.assertIn("workspace_good", ids)

    def test_chat_workspace_switch_matching_survives(self) -> None:
        from app.chat.workspace_switch import _match_target_workspace

        match = _match_target_workspace("switch to Good Co workspace please")
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual("workspace_good", match[0])

    def test_kairo_intent_matching_survives(self) -> None:
        from app.kairo_workspace_intents import infer_workspace_id_from_content

        self.assertEqual(
            "workspace_good", infer_workspace_id_from_content("please check on Good Co")
        )

    def test_skills_catalog_scan_survives(self) -> None:
        from app.skills_catalog import list_workspace_skills

        skills_dir = self.good_root / ".github" / "skills" / "demo-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: a demo\n---\nbody",
            encoding="utf-8",
        )
        skills = list_workspace_skills()
        names = {str(s.get("name") or "") for s in skills}
        self.assertIn("demo-skill", names)

    def test_operator_briefing_display_names_use_the_tolerant_loader(self) -> None:
        import app.operator_briefing as operator_briefing

        source = Path(operator_briefing.__file__).read_text(encoding="utf-8")
        self.assertIn("list_valid_workspace_project_bindings", source)
        self.assertNotIn("load_workspace_project_bindings()", source)

    def test_strict_loader_contract_is_unaffected_by_any_of_this(self) -> None:
        # The one caller that must trust every binding still fails closed.
        from app.workspace_project_bindings import (
            WorkspaceBindingError,
            load_workspace_project_bindings,
        )

        with self.assertRaises(WorkspaceBindingError):
            load_workspace_project_bindings(self.bindings_file)


if __name__ == "__main__":
    unittest.main()
