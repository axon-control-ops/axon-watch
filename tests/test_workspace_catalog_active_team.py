"""has_active_team on workspace records — lets the picker hide unstaffed workspaces.

Regression coverage: the workspace picker rendered every registered/bound
workspace, including ones with no configured company at all (e.g. legacy
project bindings from a prior integration test, or a workspace someone
registered but never staffed). On the live host that was 11 of 17
non-demo workspaces — over half the picker was dead weight.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import CompanyConfig, EmployeeConfig  # noqa: E402
from app.workspace_catalog import (  # noqa: E402
    _staffed_workspace_ids,
    _workspace_record,
    get_workspace_record,
    list_workspace_records,
)

_LOAD_CONFIGS = "app.workspace_agents.config_loader.load_workspace_agent_configs"


def _company(*, enabled_roles: tuple[str, ...]) -> CompanyConfig:
    employees = tuple(
        EmployeeConfig(name=role, role=role, enabled=True) for role in enabled_roles
    )
    return CompanyConfig(company_name="Test Co", employees=employees)


def _all_disabled_company() -> CompanyConfig:
    return CompanyConfig(
        company_name="Mothballed Co",
        employees=(EmployeeConfig(name="watcher", role="watcher", enabled=False),),
    )


class StaffedWorkspaceIdsTests(unittest.TestCase):
    def test_workspace_with_an_enabled_employee_is_staffed(self) -> None:
        with patch(
            _LOAD_CONFIGS,
            return_value=({}, {}, {"workspace_dashpro": _company(enabled_roles=("watcher",))}, []),
        ):
            self.assertIn("workspace_dashpro", _staffed_workspace_ids())

    def test_workspace_with_zero_enabled_employees_is_not_staffed(self) -> None:
        with patch(
            _LOAD_CONFIGS,
            return_value=({}, {}, {"workspace_dashpro": _all_disabled_company()}, []),
        ):
            self.assertNotIn("workspace_dashpro", _staffed_workspace_ids())

    def test_workspace_with_no_company_at_all_is_not_staffed(self) -> None:
        with patch(_LOAD_CONFIGS, return_value=({}, {}, {}, [])):
            self.assertNotIn("workspace_random_bound_id", _staffed_workspace_ids())

    def test_a_mix_of_staffed_and_unstaffed_companies(self) -> None:
        companies = {
            "workspace_dashpro": _company(enabled_roles=("watcher", "backend")),
            "workspace_mothballed": _all_disabled_company(),
        }
        with patch(_LOAD_CONFIGS, return_value=({}, {}, companies, [])):
            ids = _staffed_workspace_ids()
        self.assertIn("workspace_dashpro", ids)
        self.assertNotIn("workspace_mothballed", ids)


class WorkspaceRecordHasActiveTeamTests(unittest.TestCase):
    def test_explicit_staffed_ids_param_is_honored_without_reloading_config(self) -> None:
        with patch(_LOAD_CONFIGS) as load_mock:
            record = _workspace_record(
                "workspace_dashpro", staffed_ids=frozenset({"workspace_dashpro"})
            )
            load_mock.assert_not_called()
        self.assertTrue(record["has_active_team"])

    def test_unstaffed_workspace_reports_false(self) -> None:
        record = _workspace_record("workspace_random", staffed_ids=frozenset())
        self.assertFalse(record["has_active_team"])

    def test_omitted_staffed_ids_falls_back_to_live_config(self) -> None:
        with patch(_LOAD_CONFIGS, return_value=({}, {}, {"workspace_x": _company(enabled_roles=("lead",))}, [])):
            record = _workspace_record("workspace_x")
        self.assertTrue(record["has_active_team"])


class ListWorkspaceRecordsIntegrationTests(unittest.TestCase):
    """Exercises the real repo config — same data the live picker sees."""

    def test_only_configured_companies_are_marked_active(self) -> None:
        records = list_workspace_records(operator_surface=True)
        by_id = {r["workspace_id"]: r for r in records}
        # workspace_dashpro has a real, staffed company in config/workspace-agents.json.
        self.assertIn("workspace_dashpro", by_id)
        self.assertTrue(by_id["workspace_dashpro"]["has_active_team"])

    def test_every_record_has_the_field_populated(self) -> None:
        for record in list_workspace_records(operator_surface=True):
            self.assertIn("has_active_team", record)
            self.assertIsInstance(record["has_active_team"], bool)

    def test_get_workspace_record_also_reports_the_field(self) -> None:
        record = get_workspace_record("workspace_dashpro")
        self.assertIn("has_active_team", record)
        self.assertTrue(record["has_active_team"])


if __name__ == "__main__":
    unittest.main()
