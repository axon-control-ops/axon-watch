from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.workspace_agents import (  # noqa: E402
    build_company_roster,
    build_workspace_agent_record,
    load_workspace_agent_configs,
)
from app.workspace_agents.status import derive_agent_status, employee_status  # noqa: E402


class WorkspaceAgentsModuleTests(unittest.TestCase):
    def test_review_ready_run_marks_agent_verifying(self) -> None:
        with patch(
            "app.workspace_agents.status.list_runs",
            return_value=[
                {
                    "run_id": "run_review",
                    "workspace_id": "workspace_demo",
                    "status": "review",
                    "phase": "review_ready",
                    "ended_at": None,
                    "updated_at": "2026-07-13T14:18:34Z",
                }
            ],
        ):
            self.assertEqual("verifying", derive_agent_status("workspace_demo"))

    def test_employee_status_keeps_specialists_idle_during_workspace_run(self) -> None:
        self.assertEqual(
            "executing",
            employee_status(
                role="lead",
                schedule="on_demand",
                workspace_status="executing",
                primary=True,
            ),
        )
        self.assertEqual(
            "watching",
            employee_status(
                role="watcher",
                schedule="always_on",
                workspace_status="executing",
                primary=False,
            ),
        )
        self.assertEqual(
            "idle",
            employee_status(
                role="frontend",
                schedule="continuous",
                workspace_status="executing",
                primary=False,
            ),
        )
        self.assertEqual(
            "waiting_approval",
            employee_status(
                role="frontend",
                schedule="continuous",
                workspace_status="waiting_approval",
                primary=False,
            ),
        )

    def test_loads_agent_overrides_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "defaults": {"name_template": "{display_name} Agent"},
                        "agents": {
                            "workspace_demo": {
                                "agent_name": "Demo Agent",
                                "owns": "Demo-only work",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            configs, defaults, _companies, _template = load_workspace_agent_configs(agents_file)
            self.assertEqual("Demo Agent", configs["workspace_demo"].agent_name)
            self.assertEqual("Demo-only work", configs["workspace_demo"].owns)
            self.assertEqual("{display_name} Agent", defaults["name_template"])

    def test_builds_default_agent_name_from_display_name(self) -> None:
        record = build_workspace_agent_record(
            "workspace_demo",
            record={
                "workspace_id": "workspace_demo",
                "display_name": "dashpro",
                "connection_kind": "project_path",
            },
            configs={},
            defaults={
                "role": "lead",
                "name_template": "{display_name} Workspace Agent",
                "company_name_template": "{display_name}",
            },
            companies={},
            staffing_template=[{"role": "lead", "schedule": "on_demand"}],
        )
        self.assertEqual("DashPro Lead", record["agent_name"])
        self.assertEqual("workspace-agent-workspace_demo", record["agent_id"])
        self.assertEqual("lead", record["role"])

    def test_company_roster_applies_role_staffing(self) -> None:
        roster = build_company_roster(
            "workspace_demo",
            record={
                "workspace_id": "workspace_demo",
                "display_name": "Demo Co",
                "connection_kind": "project_path",
            },
            configs={},
            defaults={
                "role": "lead",
                "name_template": "{display_name} Lead",
                "company_name_template": "{display_name}",
            },
            companies={},
            staffing_template=[
                {"role": "lead", "schedule": "on_demand"},
                {"role": "watcher", "schedule": "always_on"},
                {"role": "frontend", "schedule": "continuous"},
            ],
        )
        self.assertEqual("Demo Co", roster["company_name"])
        self.assertEqual(3, roster["employee_count"])
        roles = [str(row["role"]) for row in roster["employees"]]  # type: ignore[index]
        self.assertEqual(["lead", "watcher", "frontend"], roles)
        watcher = next(row for row in roster["employees"] if row["role"] == "watcher")  # type: ignore[index]
        self.assertEqual("always_on", watcher["schedule"])
        self.assertEqual("watching", watcher["status"])

    def test_company_roster_only_lead_mirrors_active_run(self) -> None:
        with patch(
            "app.workspace_agents.derive_agent_status",
            return_value="executing",
        ):
            roster = build_company_roster(
                "workspace_demo",
                record={
                    "workspace_id": "workspace_demo",
                    "display_name": "Demo Co",
                    "connection_kind": "project_path",
                },
                configs={},
                defaults={
                    "role": "lead",
                    "name_template": "{display_name} Lead",
                    "company_name_template": "{display_name}",
                },
                companies={},
                staffing_template=[
                    {"role": "lead", "schedule": "on_demand"},
                    {"role": "watcher", "schedule": "always_on"},
                    {"role": "frontend", "schedule": "continuous"},
                    {"role": "backend", "schedule": "continuous"},
                ],
            )
        statuses = {str(row["role"]): str(row["status"]) for row in roster["employees"]}  # type: ignore[index]
        self.assertEqual("executing", statuses["lead"])
        self.assertEqual("watching", statuses["watcher"])
        self.assertEqual("idle", statuses["frontend"])
        self.assertEqual("idle", statuses["backend"])

    def test_loads_company_employees_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_demo": {
                                "company_name": "Demo Corp",
                                "employees": [
                                    {
                                        "name": "Lead Bot",
                                        "role": "lead",
                                        "primary": True,
                                        "schedule": "on_demand",
                                    },
                                    {
                                        "name": "Watch Bot",
                                        "role": "watcher",
                                        "schedule": "always_on",
                                        "owns": "alerts only",
                                    },
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            _configs, _defaults, companies, _template = load_workspace_agent_configs(agents_file)
            self.assertEqual("Demo Corp", companies["workspace_demo"].company_name)
            self.assertEqual(2, len(companies["workspace_demo"].employees))
            self.assertEqual("watcher", companies["workspace_demo"].employees[1].role)


class ControlPlaneWorkspaceAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_agents_index_includes_bound_workspace_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            agents_file = Path(tempdir) / "agents.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_bound_demo": {
                                "project_root": str(project_root),
                                "display_name": "Bound demo",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            agents_file.write_text(
                json.dumps(
                    {
                        "agents": {
                            "workspace_bound_demo": {
                                "agent_name": "Bound Demo Agent",
                                "owns": "Bound demo work only",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                response = self.client.get("/api/agents?scope=operator")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        by_workspace = {item["workspace_id"]: item for item in payload["items"]}
        self.assertIn("workspace_bound_demo", by_workspace)
        agent = by_workspace["workspace_bound_demo"]
        self.assertEqual("Bound Demo Agent", agent["agent_name"])
        self.assertEqual("Bound demo work only", agent["owns"])
        self.assertEqual("idle", agent["status"])

    def test_workspace_agent_show_returns_configured_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            agents_file = Path(tempdir) / "agents.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_bound_demo": {
                                "project_root": str(project_root),
                                "display_name": "Bound demo",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            agents_file.write_text(
                json.dumps(
                    {
                        "agents": {
                            "workspace_bound_demo": {
                                "agent_name": "Bound Demo Agent",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                response = self.client.get("/api/workspaces/workspace_bound_demo/agent")

        self.assertEqual(200, response.status_code)
        self.assertEqual("Bound Demo Agent", response.json()["agent_name"])

    def test_workspace_agent_status_reflects_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_bound_demo": {
                                "project_root": str(project_root),
                                "display_name": "Bound demo",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                self.client.post(
                    "/api/runs",
                    json={
                        "workspace_id": "workspace_bound_demo",
                        "mode": "agent",
                        "summary": "Active agent work",
                    },
                )
                response = self.client.get("/api/workspaces/workspace_bound_demo/agent")

        self.assertEqual(200, response.status_code)
        self.assertIn(response.json()["status"], {"executing", "watching", "planning"})

    def test_workspace_company_returns_role_based_employees(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            project_root = Path(tempdir) / "bound-project"
            project_root.mkdir()
            bindings_file = Path(tempdir) / "bindings.json"
            agents_file = Path(tempdir) / "agents.json"
            bindings_file.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_bound_demo": {
                                "project_root": str(project_root),
                                "display_name": "Bound demo",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_bound_demo": {
                                "company_name": "Bound Co",
                                "employees": [
                                    {
                                        "name": "Bound Lead",
                                        "role": "lead",
                                        "primary": True,
                                        "schedule": "on_demand",
                                    },
                                    {
                                        "name": "Bound Watch",
                                        "role": "watcher",
                                        "schedule": "always_on",
                                    },
                                    {
                                        "name": "Bound UI",
                                        "role": "frontend",
                                        "schedule": "continuous",
                                    },
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AXON_WATCH_WORKSPACE_BINDINGS_FILE": str(bindings_file),
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_PROJECT_ROOT_ALLOWLIST": str(tempdir),
                },
                clear=False,
            ):
                response = self.client.get("/api/workspaces/workspace_bound_demo/company")
                roles = self.client.get("/api/company-roles")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("Bound Co", payload["company"]["company_name"])
        self.assertEqual(3, payload["company"]["employee_count"])
        role_ids = [item["role"] for item in payload["company"]["employees"]]
        self.assertEqual(["lead", "watcher", "frontend"], role_ids)
        self.assertEqual(200, roles.status_code)
        self.assertGreaterEqual(roles.json()["count"], 5)


if __name__ == "__main__":
    unittest.main()
