from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import run_store, worker_scheduler_settings_store  # noqa: E402
from app.runs.service import create_run, fail_run, get_run, stop_run  # noqa: E402
from app.workspace_agents import build_company_roster  # noqa: E402
from app.workspace_agents.scheduler import run_continuous_worker_tick  # noqa: E402
from app.workspace_agents.status import active_role_run_id, active_role_run_status  # noqa: E402


class WorkspaceAgentSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)

    def test_default_agents_file_resolves_to_repo_config_not_services(self) -> None:
        from app.workspace_agents.config_loader import default_agents_file, load_workspace_agent_configs

        path = default_agents_file()
        self.assertEqual("workspace-agents.json", path.name)
        self.assertIn("/config/", str(path))
        self.assertNotIn("/services/config/", str(path))
        self.assertTrue(path.is_file(), msg=f"missing agents file at {path}")
        _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
        self.assertIn("workspace_dashpro", companies)
        self.assertTrue(
            any(
                emp.schedule in {"always_on", "continuous"}
                for emp in companies["workspace_dashpro"].employees
            )
        )

    def test_create_run_persists_employee_role(self) -> None:
        created = create_run(
            workspace_id="workspace_role_tag",
            mode="agent",
            summary="Frontend continuous shift",
            employee_role="frontend",
        )
        self.assertEqual("frontend", created.get("employee_role"))
        stored = run_store.get_run(str(created["run_id"]))
        assert stored is not None
        self.assertEqual("frontend", stored.get("employee_role"))
        self.assertEqual("executing", active_role_run_status("workspace_role_tag", "frontend"))

    def test_active_role_run_helpers_ignore_paused_shift(self) -> None:
        created = create_run(
            workspace_id="workspace_role_paused",
            mode="agent",
            summary="Backend continuous shift",
            employee_role="backend",
        )
        run_id = str(created["run_id"])
        stop_run(run_id)
        self.assertEqual("paused", get_run(run_id)["phase"])
        self.assertIsNone(active_role_run_status("workspace_role_paused", "backend"))
        self.assertIsNone(active_role_run_id("workspace_role_paused", "backend"))

    def test_company_roster_specialist_reflects_role_tagged_run(self) -> None:
        create_run(
            workspace_id="workspace_demo",
            mode="agent",
            summary="Untagged workspace work",
        )
        create_run(
            workspace_id="workspace_demo",
            mode="agent",
            summary="Shell Craft continuous shift",
            employee_role="frontend",
        )
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
        self.assertEqual("executing", statuses["frontend"])
        self.assertEqual("idle", statuses["backend"])

    def test_continuous_worker_tick_starts_role_tagged_runs_once(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_sched_demo": {
                                "company_name": "Sched Co",
                                "employees": [
                                    {
                                        "name": "Sched Lead",
                                        "role": "lead",
                                        "primary": True,
                                        "schedule": "on_demand",
                                    },
                                    {
                                        "name": "Sched Watch",
                                        "role": "watcher",
                                        "schedule": "always_on",
                                    },
                                    {
                                        "name": "Sched UI",
                                        "role": "frontend",
                                        "schedule": "continuous",
                                    },
                                    {
                                        "name": "Sched API",
                                        "role": "backend",
                                        "schedule": "on_demand",
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
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_WORKER_SCHEDULER": "1",
                    "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "0",
                },
                clear=False,
            ):
                worker_scheduler_settings_store.patch_settings({"scheduler_enabled": True})
                first = run_continuous_worker_tick()
                second = run_continuous_worker_tick()

        roles = sorted(
            str(run.get("employee_role") or "")
            for run in first
            if run.get("employee_role")
        )
        self.assertEqual(["frontend", "watcher"], roles)
        self.assertEqual([], second)
        self.assertTrue(all(run.get("employee_role") for run in first))
        self.assertEqual("executing", active_role_run_status("workspace_sched_demo", "frontend"))
        self.assertEqual("executing", active_role_run_status("workspace_sched_demo", "watcher"))

    def test_dispatch_crash_fails_run_instead_of_leaving_executing(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        created = create_run(
            workspace_id="workspace_worker_fail",
            mode="agent",
            summary="Backend continuous shift",
            employee_role="backend",
        )
        run_id = str(created["run_id"])
        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=RuntimeError("simulated dispatch crash"),
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id="workspace_worker_fail",
                employee=EmployeeConfig(
                    name="API Craft",
                    role="backend",
                    owns="APIs and persistence",
                    schedule="continuous",
                ),
                run_record=created,
            )

        self.assertFalse(dispatched)
        assert finalized is not None
        self.assertEqual("failed", finalized["phase"])
        stored = run_store.get_run(run_id)
        assert stored is not None
        self.assertEqual("failed", stored["phase"])
        # No non-terminal role-tagged run remains, so the role is free for the next tick.
        self.assertIsNone(active_role_run_status("workspace_worker_fail", "backend"))

    def test_dispatch_start_records_worker_heartbeat_receipt(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        created = create_run(
            workspace_id="workspace_worker_heartbeat",
            mode="agent",
            summary="Backend continuous shift",
            employee_role="backend",
        )
        run_id = str(created["run_id"])
        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            return_value={"dispatched": True, "runtime_label": "test", "content": "done"},
        ):
            dispatch_continuous_worker_run(
                workspace_id="workspace_worker_heartbeat",
                employee=EmployeeConfig(
                    name="API Craft",
                    role="backend",
                    owns="APIs and persistence",
                    schedule="continuous",
                ),
                run_record=created,
            )

        history = run_store.list_history(get_run(run_id)["history_ref"])
        receipt_types = [str(item.get("receipt", {}).get("type") or "") for item in history]
        self.assertIn("worker_dispatch_started", receipt_types)

    def test_continuous_worker_tick_skips_role_after_usage_limit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_axon_watch": {
                                "company_name": "Axon-X",
                                "employees": [
                                    {
                                        "name": "Quinn",
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
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_WORKER_SCHEDULER": "1",
                    "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "0",
                },
                clear=False,
            ):
                worker_scheduler_settings_store.patch_settings({"scheduler_enabled": True})
                failed = create_run(
                    workspace_id="workspace_axon_watch",
                    mode="agent",
                    summary="Quinn: continuous worker shift",
                    employee_role="integrations",
                )
                fail_run(
                    failed["run_id"],
                    receipt_summary=(
                        "Lane B agent fallback reply generated "
                        "(ActionRequiredError: Increase limits for faster responses "
                        "You're out of usage.)"
                    ),
                )
                started = run_continuous_worker_tick()

        self.assertEqual([], started)


if __name__ == "__main__":
    unittest.main()
