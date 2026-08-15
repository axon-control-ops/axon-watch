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

from app.persistence import (  # noqa: E402
    constitution_registry_store,
    run_store,
    task_store,
    worker_scheduler_settings_store,
)
from app.runs.service import create_run, fail_run, get_run, stop_run  # noqa: E402
from app.workspace_agents import build_company_roster  # noqa: E402
from app.workspace_agents.scheduler import run_continuous_worker_tick  # noqa: E402
from app.workspace_agents.scheduler import run_observation_tick  # noqa: E402
from app.workspace_agents.status import active_role_run_id, active_role_run_status  # noqa: E402


def _seed_open_task(*, workspace_id: str, owner_role: str, goal: str = "Seeded leased work") -> dict:
    return task_store.create_task(
        workspace_id=workspace_id,
        goal=goal,
        owner_role=owner_role,
        acceptance_criteria="receipts prove the goal",
    )


class WorkspaceAgentSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        constitution_registry_store.reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(constitution_registry_store.reset_store)

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
            _seed_open_task(
                workspace_id="workspace_sched_demo",
                owner_role="frontend",
                goal="Frontend continuous task",
            )
            _seed_open_task(
                workspace_id="workspace_sched_demo",
                owner_role="watcher",
                goal="Watcher continuous task",
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
        self.assertTrue(all(run.get("task_id") for run in first))
        self.assertEqual("executing", active_role_run_status("workspace_sched_demo", "frontend"))
        self.assertEqual("executing", active_role_run_status("workspace_sched_demo", "watcher"))

    def test_continuous_worker_tick_skips_when_no_open_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            agents_file = Path(tempdir) / "agents.json"
            agents_file.write_text(
                json.dumps(
                    {
                        "companies": {
                            "workspace_sched_empty": {
                                "company_name": "Empty Co",
                                "employees": [
                                    {
                                        "name": "Empty UI",
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
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_WORKER_SCHEDULER": "1",
                    "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "0",
                },
                clear=False,
            ):
                worker_scheduler_settings_store.patch_settings({"scheduler_enabled": True})
                started = run_continuous_worker_tick()

        self.assertEqual([], started)

    def test_observation_tick_runs_watch_sources_when_worker_scheduler_off(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "AXON_WATCH_OBSERVATION_SCHEDULER": "1",
                    "AXON_WATCH_WORKER_SCHEDULER": "1",
                },
                clear=False,
            ),
            patch(
                "app.workspace_agents.company_work_sources.run_scheduled_work_sources",
                return_value={
                    "recovered_leases": [],
                    "sources": {"ci_stale_signal_sweep": {"checked": 1}},
                },
            ) as work_sources,
        ):
            worker_scheduler_settings_store.patch_settings(
                {
                    "watcher_scheduler_enabled": True,
                    "scheduler_enabled": False,
                }
            )
            observed = run_observation_tick()
            started = run_continuous_worker_tick()

        self.assertTrue(observed["enabled"])
        self.assertEqual([], started)
        work_sources.assert_any_call(observation_only=True)

    def test_dispatch_crash_fails_run_instead_of_leaving_executing(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run

        opened = _seed_open_task(
            workspace_id="workspace_worker_fail",
            owner_role="backend",
            goal="Dispatch crash task",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_worker_fail-backend",
        )
        created = create_run(
            workspace_id="workspace_worker_fail",
            mode="agent",
            summary="Backend continuous shift",
            employee_role="backend",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        run_id = str(created["run_id"])
        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            side_effect=RuntimeError("simulated dispatch crash"),
        ), patch(
            "app.workspace_agents.worker_dispatch.prepare_worker_ide_stream",
            return_value=None,
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

        opened = _seed_open_task(
            workspace_id="workspace_worker_heartbeat",
            owner_role="backend",
            goal="Heartbeat task",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_worker_heartbeat-backend",
        )
        created = create_run(
            workspace_id="workspace_worker_heartbeat",
            mode="agent",
            summary="Backend continuous shift",
            employee_role="backend",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        run_id = str(created["run_id"])
        with (
            patch(
                "app.workspace_agents.worker_dispatch.generate_lane_b_result",
                return_value={"dispatched": True, "runtime_label": "test", "content": "done"},
            ),
            patch(
                "app.workspace_agents.worker_dispatch.finalize_lane_b_agent_run",
                return_value=(False, None),
            ),
            patch(
                "app.workspace_agents.worker_dispatch.prepare_worker_ide_stream",
                return_value=None,
            ),
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

    def test_full_access_no_change_delivery_reopens_task(self) -> None:
        from app.workspace_agents.config_loader import EmployeeConfig
        from app.workspace_agents.execution_policy import role_execution_policy
        from app.workspace_agents.worker_dispatch import dispatch_continuous_worker_run
        from app.workspace_delivery.publish import PublishResult

        opened = _seed_open_task(
            workspace_id="workspace_worker_noop",
            owner_role="backend",
            goal="Implement the backend fix",
        )
        leased = task_store.lease_task(
            opened["task_id"],
            lease_holder="employee-workspace_worker_noop-backend",
        )
        created = create_run(
            workspace_id="workspace_worker_noop",
            mode="agent",
            summary="Backend continuous shift",
            employee_role="backend",
            task_id=leased["task_id"],
            require_leased_task=True,
        )
        run_id = str(created["run_id"])
        with patch(
            "app.workspace_agents.worker_dispatch.generate_lane_b_result",
            return_value={
                "dispatched": True,
                "runtime_label": "test",
                "content": "No files changed.\n\nConfidence: 10/10",
            },
        ), patch(
            "app.workspace_agents.worker_dispatch.resolve_worker_execution_policy",
            return_value=role_execution_policy("backend"),
        ), patch(
            "app.workspace_agents.worker_dispatch.finalize_lane_b_agent_run",
            return_value=(True, {"phase": "executing"}),
        ), patch(
            "app.workspace_agents.verifier_contract.run_requires_acceptance_evidence",
            return_value=True,
        ), patch(
            "app.workspace_agents.verifier_contract.has_passing_acceptance_evidence",
            return_value=True,
        ), patch(
            "app.workspace_delivery.publish_worker_isolation",
            return_value=PublishResult(
                ok=True,
                stage="no_change",
                delivery={"delivery_id": "delivery-noop"},
                detail="no changes",
                cleanup_isolation=True,
            ),
        ), patch(
            "app.workspace_agents.worker_dispatch.prepare_worker_ide_stream",
            return_value=None,
        ):
            dispatched, finalized = dispatch_continuous_worker_run(
                workspace_id="workspace_worker_noop",
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
        task = task_store.get_task(leased["task_id"])
        assert task is not None
        self.assertEqual("open", task["status"])
        history = run_store.list_history(get_run(run_id)["history_ref"])
        summaries = [
            str(item.get("receipt", {}).get("summary") or "").lower()
            for item in history
        ]
        self.assertTrue(
            any("no changed files" in summary or "completion gate" in summary for summary in summaries),
            summaries,
        )

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
            with (
                patch.dict(
                    os.environ,
                    {
                        "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                        "AXON_WATCH_WORKER_SCHEDULER": "1",
                        "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "0",
                    },
                    clear=False,
                ),
                patch(
                    "app.cli_runtime.cursor_usage_probe.probe_cursor_usage",
                    return_value={},
                ),
                patch(
                    "app.cli_runtime.cursor_usage_probe.cursor_usage_allows_agent_retry",
                    return_value=False,
                ),
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

    def test_continuous_worker_tick_skips_role_after_runtime_auth_failure(self) -> None:
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
                                        "name": "Rowan",
                                        "role": "watcher",
                                        "schedule": "always_on",
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
                    summary="Rowan: continuous worker shift",
                    employee_role="watcher",
                )
                fail_run(
                    failed["run_id"],
                    receipt_summary=(
                        "Lane B agent fallback reply generated "
                        "(Cursor is installed but not signed in. Run `cursor agent login` "
                        "or unlock /vault.; Cursor Cloud Agent unavailable)"
                    ),
                )
                started = run_continuous_worker_tick()

        self.assertEqual([], started)

    def test_continuous_worker_tick_retries_after_session_interrupt_failure(self) -> None:
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
                                        "name": "Reed",
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
                    summary="Reed: continuous worker shift",
                    employee_role="backend",
                )
                fail_run(
                    failed["run_id"],
                    receipt_summary="Cursor CLI exited with status 143.",
                )
                _seed_open_task(
                    workspace_id="workspace_axon_watch",
                    owner_role="backend",
                    goal="Retry after interrupt",
                )
                started = run_continuous_worker_tick()

        roles = [str(run.get("employee_role") or "") for run in started]
        self.assertEqual(["backend"], roles)
        self.assertTrue(all(run.get("task_id") for run in started))

    def test_scheduler_dispatch_records_constitution_decision_trace(self) -> None:
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
                                        "name": "Trace",
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
                    "AXON_WATCH_WORKSPACE_AGENTS_FILE": str(agents_file),
                    "AXON_WATCH_WORKER_SCHEDULER": "1",
                    "AXON_WATCH_WORKER_SCHEDULER_DISPATCH": "0",
                },
                clear=False,
            ):
                worker_scheduler_settings_store.patch_settings({"scheduler_enabled": True})
                task = _seed_open_task(
                    workspace_id="workspace_axon_watch",
                    owner_role="backend",
                    goal="Trace a scheduler dispatch",
                )
                started = run_continuous_worker_tick()

        self.assertEqual(1, len(started))
        decisions = constitution_registry_store.list_decisions(task_id=task["task_id"])
        self.assertEqual(1, len(decisions))
        self.assertEqual("worker_scheduler", decisions[0]["actor"])
        self.assertEqual("dispatch", decisions[0]["decision"])
        self.assertEqual("CAP-034", decisions[0]["capability_id"])
        evidence = constitution_registry_store.list_evidence(
            source_table="workspace_tasks",
            task_id=task["task_id"],
        )
        self.assertEqual(1, len(evidence))
        self.assertEqual(decisions[0]["decision_id"], evidence[0]["decision_id"])


if __name__ == "__main__":
    unittest.main()
