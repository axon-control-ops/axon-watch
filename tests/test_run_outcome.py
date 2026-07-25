"""Roster outcome helpers expose real failure detail, not bare FAILED."""

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
from app.workspace_agents.run_outcome import latest_role_run_outcome  # noqa: E402


class RunOutcomeTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_fail_run_current_step_keeps_reason(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        failed = fail_run(
            created["run_id"],
            receipt_summary="Lane B agent fallback reply generated (ActionRequiredError: out of usage)",
        )
        self.assertEqual("failed", failed["phase"])
        self.assertIn("out of usage", failed["current_step"])
        self.assertNotEqual("Run failed", failed["current_step"])

    def test_latest_role_outcome_reads_failure_receipt(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Shell Craft: continuous worker shift",
            employee_role="frontend",
        )
        fail_run(
            created["run_id"],
            receipt_summary="Lane B agent fallback reply generated (ActionRequiredError: out of usage)",
        )
        outcome = latest_role_run_outcome("workspace_axon_watch", "frontend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("out of usage", outcome["detail"])

    def test_latest_role_outcome_normalizes_lane_b_fallback_wrapper(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Control Plane: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            created["run_id"],
            receipt_summary=(
                "Lane B agent fallback reply generated "
                "(ActionRequiredError: Increase limits for faster responses You're out of usage.)"
            ),
        )
        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertNotIn("Lane B agent fallback", outcome["detail"])
        self.assertIn("out of usage", outcome["detail"])

    def test_latest_role_outcome_prefers_terminal_failure_over_paused_shift(self) -> None:
        failed = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Backend: continuous worker shift",
            employee_role="backend",
        )
        fail_run(
            failed["run_id"],
            receipt_summary="cursor agent unavailable",
        )

        paused = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Backend: follow-up shift",
            employee_role="backend",
        )
        stop_run(paused["run_id"])

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("cursor agent unavailable", outcome["detail"])

    def test_latest_role_outcome_reads_failure_detail_from_history(self) -> None:
        created = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Integrations: connector parity shift",
            employee_role="integrations",
        )
        fail_run(
            created["run_id"],
            receipt_summary="control_plane probe unavailable (Connection refused)",
        )
        stored = run_store.get_run(created["run_id"])
        assert stored is not None
        stored["current_step"] = "Run failed"
        run_store.save_run(stored)

        outcome = latest_role_run_outcome("workspace_axon_watch", "integrations")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("Connection refused", outcome["detail"])

    def test_latest_role_outcome_skips_control_plane_restart_interruptions(self) -> None:
        real_failure = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: connector health shift",
            employee_role="watcher",
        )
        fail_run(
            real_failure["run_id"],
            receipt_summary="control_plane probe unavailable (Connection refused)",
        )

        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: continuous worker shift",
            employee_role="watcher",
        )
        fail_run(
            restarted["run_id"],
            receipt_summary="Run interrupted by control-plane restart",
            actor="control-plane",
        )

        outcome = latest_role_run_outcome("workspace_axon_watch", "watcher")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("Connection refused", outcome["detail"])
        self.assertEqual(real_failure["run_id"], outcome["run_id"])

    def test_latest_role_outcome_omits_restart_only_failure(self) -> None:
        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Rowan: continuous worker shift",
            employee_role="watcher",
        )
        fail_run(
            restarted["run_id"],
            receipt_summary="Run interrupted by control-plane restart",
            actor="control-plane",
        )

        self.assertIsNone(latest_role_run_outcome("workspace_axon_watch", "watcher"))

    def test_latest_role_outcome_skips_employee_restart_cancelled_run(self) -> None:
        real_failure = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: backend shift",
            employee_role="backend",
        )
        fail_run(
            real_failure["run_id"],
            receipt_summary="verify:contracts — test_run_outcome.py: assertion failed",
        )

        restarted = create_run(
            workspace_id="workspace_axon_watch",
            mode="agent",
            summary="Reed: continuous worker shift",
            employee_role="backend",
        )
        from app.runs.restart_reconcile import interrupt_run_on_restart

        cancelled = interrupt_run_on_restart(restarted["run_id"])
        assert cancelled is not None
        self.assertEqual("cancelled", cancelled["phase"])

        outcome = latest_role_run_outcome("workspace_axon_watch", "backend")
        assert outcome is not None
        self.assertEqual("failed", outcome["outcome"])
        self.assertIn("assertion failed", outcome["detail"])
        self.assertEqual(real_failure["run_id"], outcome["run_id"])


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
