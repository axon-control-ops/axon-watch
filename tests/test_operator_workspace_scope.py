from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_workspace_scope import (  # noqa: E402
    filter_operator_workspace_records,
    is_demo_isolated_workspace,
    is_operator_surface_workspace,
)


class OperatorWorkspaceScopeTests(unittest.TestCase):
    def test_demo_ids_are_recognized(self) -> None:
        self.assertTrue(is_demo_isolated_workspace("workspace_smoke"))
        self.assertTrue(is_demo_isolated_workspace("workspace_bootstrap"))
        self.assertFalse(is_demo_isolated_workspace("workspace_dashpro"))

    def test_bound_project_always_surfaces(self) -> None:
        record = {
            "workspace_id": "workspace_dashpro",
            "connection_kind": "project_path",
            "display_name": "DashPro",
        }
        self.assertTrue(is_operator_surface_workspace(record))

    def test_demo_isolated_hidden_from_operator_surface(self) -> None:
        record = {
            "workspace_id": "workspace_smoke",
            "connection_kind": "isolated_root",
        }
        self.assertFalse(is_operator_surface_workspace(record))

    def test_filter_keeps_bound_and_drops_demo(self) -> None:
        records = [
            {"workspace_id": "workspace_dashpro", "connection_kind": "project_path"},
            {"workspace_id": "workspace_smoke", "connection_kind": "isolated_root"},
            {"workspace_id": "workspace_axon_watch", "connection_kind": "project_path"},
        ]
        filtered = filter_operator_workspace_records(records)
        ids = {row["workspace_id"] for row in filtered}
        self.assertEqual({"workspace_dashpro", "workspace_axon_watch"}, ids)


if __name__ == "__main__":
    unittest.main()
