"""Company roster API surfaces run-outcome detail and active-run ids."""

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
from app.runs.service import create_run, fail_run, stop_run  # noqa: E402


class RunOutcomeRosterApiTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_company_roster_surfaces_integrations_failure_detail(self) -> None:
        failure_detail = (
            "verify:connector-parity — test3-watch-connectors.sh: "
            "control_plane probe unavailable (Connection refused)"
        )
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
                                        "name": "Bound Bridge",
                                        "role": "integrations",
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
                created = create_run(
                    workspace_id="workspace_bound_demo",
                    mode="agent",
                    summary="Bridge: connector parity shift",
                    employee_role="integrations",
                )
                fail_run(created["run_id"], receipt_summary=failure_detail)
                response = self.client.get("/api/workspaces/workspace_bound_demo/company")

        self.assertEqual(200, response.status_code)
        employees = response.json()["company"]["employees"]
        bridge = next(row for row in employees if row["role"] == "integrations")
        self.assertEqual("failed", bridge.get("last_outcome"))
        self.assertIn("Connection refused", str(bridge.get("last_outcome_detail")))
        self.assertNotIn("Run failed", str(bridge.get("last_outcome_detail")))

    def test_company_roster_surfaces_active_run_id_for_executing_shift(self) -> None:
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
                                        "name": "Bound Backend",
                                        "role": "backend",
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
                created = create_run(
                    workspace_id="workspace_bound_demo",
                    mode="agent",
                    summary="Backend: continuous worker shift",
                    employee_role="backend",
                )
                response = self.client.get("/api/workspaces/workspace_bound_demo/company")

        self.assertEqual(200, response.status_code)
        backend = response.json()["company"]["employees"][0]
        self.assertEqual("backend", backend["role"])
        self.assertEqual("executing", backend["status"])
        self.assertEqual(created["run_id"], backend.get("active_run_id"))

    def test_company_roster_omits_active_run_id_for_paused_shift(self) -> None:
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
                                        "name": "Bound Backend",
                                        "role": "backend",
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
                created = create_run(
                    workspace_id="workspace_bound_demo",
                    mode="agent",
                    summary="Backend: paused worker shift",
                    employee_role="backend",
                )
                stop_run(created["run_id"])
                response = self.client.get("/api/workspaces/workspace_bound_demo/company")

        self.assertEqual(200, response.status_code)
        backend = response.json()["company"]["employees"][0]
        self.assertEqual("backend", backend["role"])
        self.assertEqual("idle", backend["status"])
        self.assertNotIn("active_run_id", backend)


if __name__ == "__main__":
    unittest.main()
