from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.worker_prompt import build_continuous_worker_prompt  # noqa: E402
from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402


class WorkspaceWorkerPromptLeadPlanTests(unittest.TestCase):
    def test_lead_plan_follow_up_prompt_embeds_plan_evidence(self) -> None:
        from app.persistence import run_store, task_store
        from app.workspace_agents import lead_plan_store

        isolate_control_plane_db(self, run_store)
        task_store.reset_store()
        lead_plan_store.reset_store()
        self.addCleanup(task_store.reset_store)
        self.addCleanup(lead_plan_store.reset_store)

        watcher = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Check DashPro health after restart.",
            owner_role="watcher",
            acceptance_criteria="Health receipt captured.",
        )
        watcher = task_store.complete_task(
            str(watcher["task_id"]),
            terminal_outcome="completed",
            run_id="run_cass_health_1",
        )
        integrations = task_store.create_task(
            workspace_id="workspace_dashpro",
            goal="Fix deployment linkage after watcher evidence.",
            owner_role="integrations",
            acceptance_criteria="Deployment evidence captured.",
        )
        plan = lead_plan_store.persist_plan(
            workspace_id="workspace_dashpro",
            plan={
                "goal": "Please check this and fix",
                "mode": "decompose",
                "items": [
                    {
                        "id": "plan-01-watcher",
                        "owner_role": "watcher",
                        "title": "Check current DashPro service health.",
                    },
                    {
                        "id": "plan-02-integrations",
                        "owner_role": "integrations",
                        "title": "Continue from watcher evidence.",
                    },
                ],
            },
            plan_key_to_task_id={
                "plan-01-watcher": str(watcher["task_id"]),
                "plan-02-integrations": str(integrations["task_id"]),
            },
        )
        lead_plan_store.append_receipt(
            plan_id=str(plan["plan_id"]),
            workspace_id="workspace_dashpro",
            kind="lead_specialist_status_posted",
            payload={
                "run_id": "run_cass_health_1",
                "task_id": str(watcher["task_id"]),
                "phase": "completed",
            },
        )

        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_dashpro",
                employee=EmployeeConfig(
                    name="Dana",
                    role="lead",
                    owns="DashPro product priorities and handoffs",
                    schedule="on_demand",
                ),
                task={
                    "task_id": "task-lead-followup",
                    "goal": (
                        'Lead: advance "Please check this and fix" toward Done '
                        f"[plan {plan['plan_id']}] — after Cass (watcher) completed."
                    ),
                    "acceptance_criteria": (
                        f"Sole truth: advance plan {plan['plan_id']} — "
                        "Please check this and fix."
                    ),
                },
            )

        self.assertIn("Lead plan evidence packet", prompt)
        self.assertIn(str(plan["plan_id"]), prompt)
        self.assertIn("plan-01-watcher: watcher completed", prompt)
        self.assertIn("run=run_cass_health_1", prompt)
        self.assertIn("plan-02-integrations: integrations open", prompt)
        self.assertIn("lead_specialist_status_posted", prompt)


if __name__ == "__main__":
    unittest.main()
