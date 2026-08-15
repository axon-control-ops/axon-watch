from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.assignment_messages import (  # noqa: E402
    assignment_card,
    assignment_card_title,
    is_lead_self_assignment,
)
from app.workspace_agents.lead_verification_handoff import (  # noqa: E402
    build_verification_acceptance_evaluation,
    enqueue_specialist_verification_task,
    extract_verification_commands,
    is_verification_task,
    looks_like_verification_handoff,
    verification_worker_prompt_clause,
)


MARCO_REPLY = """
## Receipts
- **Tests:** `npm test -- tests/unit/services/staffVisibility.test.ts` — blocked in this headless runtime
- **Live verify:** `npx tsx services/ops/verify-lesego-dimakatso-staff.ts` — not run here

### Blockers / Lead next
- I could not execute Jest or the live verify script in this worker runtime — Lead should run the test + read-only verify on a scoped terminal job before any APPLY=true write.

Confidence: 8/10
"""


class AssignmentCardCopyTests(unittest.TestCase):
    def test_lead_self_assignment_uses_pickup_copy(self) -> None:
        self.assertTrue(is_lead_self_assignment("lead"))
        self.assertEqual(
            assignment_card_title(
                assignee_name="Dana",
                assignee_role="lead",
                state="started",
            ),
            "Dana picked up a follow-up board ticket.",
        )
        card = assignment_card(
            assignee_name="Dana",
            assignee_role="lead",
            goal="Lead follow-up after Marco (backend): verify receipts",
            task_id="task-demo123456789",
            run_id="run-demo",
            state="started",
            lead_name="Dana",
        )
        self.assertIn("Dana picked up a follow-up board ticket.", card)
        self.assertNotIn("queued a Lead assignment for Dana", card)

    def test_specialist_assignment_keeps_dispatcher_copy(self) -> None:
        card = assignment_card(
            assignee_name="Marco",
            assignee_role="backend",
            goal="Fix staff visibility",
            task_id="task-demo123456789",
            run_id="run-demo",
            state="queued",
            lead_name="Dana",
        )
        self.assertIn("Dana queued a Backend assignment for Marco.", card)


class LeadVerificationHandoffTests(unittest.TestCase):
    def test_detects_marco_style_verification_handoff(self) -> None:
        self.assertTrue(
            looks_like_verification_handoff(
                blockers="blocked in this headless runtime",
                reply_text=MARCO_REPLY,
            )
        )

    def test_ignores_decision_only_lead_next(self) -> None:
        self.assertFalse(
            looks_like_verification_handoff(
                lead_next="Lead: decide when to ship after CI is green.",
                reply_text="All checks passed.\nConfidence: 9/10",
            )
        )

    def test_extracts_verify_commands(self) -> None:
        commands = extract_verification_commands(MARCO_REPLY)
        self.assertIn("npm test -- tests/unit/services/staffVisibility.test.ts", commands)
        self.assertIn("npx tsx services/ops/verify-lesego-dimakatso-staff.ts", commands)

    def test_rejects_malformed_retry_commands(self) -> None:
        commands = extract_verification_commands(
            "Retry `npm test- tests/services/lessonActivitiesService.schema-contract.test.ts`"
        )
        self.assertEqual([], commands)

    def test_rejects_shell_operators_in_verification_commands(self) -> None:
        commands = extract_verification_commands(
            "Retry `npm test -- tests/unit/safe.test.ts && touch /tmp/unsafe`"
        )
        self.assertEqual([], commands)

    def test_enqueue_verification_task_is_idempotent(self) -> None:
        from app.persistence import task_store

        task_store.reset_store()
        first = enqueue_specialist_verification_task(
            workspace_id="workspace_demo",
            employee_name="Marco",
            employee_role="backend",
            run_id="run_marco_verify_1",
            reply_text=MARCO_REPLY,
            blockers="headless runtime blocked shell",
        )
        second = enqueue_specialist_verification_task(
            workspace_id="workspace_demo",
            employee_name="Marco",
            employee_role="backend",
            run_id="run_marco_verify_1",
            reply_text=MARCO_REPLY,
        )
        self.assertIsNotNone(first)
        self.assertEqual(first["task_id"], second["task_id"])
        self.assertEqual("backend", first["owner_role"])
        self.assertTrue(str(first["goal"]).startswith("Verification after Marco"))
        self.assertIn("tests", first.get("allowed_paths") or [])

    def test_find_and_lease_open_verification_task(self) -> None:
        from app.persistence import task_store
        from app.workspace_agents.lead_verification_handoff import (
            find_open_verification_task,
            try_lease_open_verification_task,
        )

        task_store.reset_store()
        created = enqueue_specialist_verification_task(
            workspace_id="workspace_demo",
            employee_name="Marco",
            employee_role="backend",
            run_id="run_marco_verify_2",
            reply_text=MARCO_REPLY,
        )
        self.assertIsNotNone(created)
        found = find_open_verification_task("workspace_demo", "backend")
        self.assertEqual(created["task_id"], found["task_id"])
        leased = try_lease_open_verification_task(
            workspace_id="workspace_demo",
            owner_role="backend",
            lease_holder="test-lease",
        )
        self.assertEqual("leased", leased["status"])

    def test_verification_prompt_clause_requires_terminal_jobs(self) -> None:
        task = {
            "goal": (
                "Verification after Marco (backend): run scoped verify commands — "
                "`npm test -- tests/unit/services/staffVisibility.test.ts` "
                "[from run run_demo]"
            )
        }
        self.assertTrue(is_verification_task(task))
        clause = verification_worker_prompt_clause(
            workspace_id="workspace_dashpro",
            task=task,
        )
        self.assertIn("VERIFICATION SHIFT", clause)
        self.assertIn("axon-agent-terminal-job", clause)
        self.assertIn("staffVisibility.test.ts", clause)

    def test_verification_commands_extract_test_paths_from_acceptance(self) -> None:
        from app.workspace_agents.lead_verification_handoff import (
            verification_commands_for_task,
        )

        task = {
            "goal": "Verification after Marco (backend): npm test; npx jest",
            "acceptance_criteria": (
                "Run tests: `tests/unit/navigation/screenRoleGuard.test.ts` and "
                "`tests/unit/services/adminStaffScreeningCounters.test.ts`."
            ),
        }
        commands = verification_commands_for_task(task)
        self.assertIn(
            "npm test -- tests/unit/navigation/screenRoleGuard.test.ts",
            commands,
        )
        self.assertIn(
            "npm test -- tests/unit/services/adminStaffScreeningCounters.test.ts",
            commands,
        )

    def test_verification_task_is_not_implementation(self) -> None:
        from app.workspace_agents.completion_gate import implementation_requested

        task = {
            "goal": "Verification after Marco (backend): run scoped verify commands",
            "owner_role": "backend",
        }
        self.assertFalse(implementation_requested(task))

    def test_verification_acceptance_passes_on_completed_terminal_jobs(self) -> None:
        from unittest.mock import patch

        task = {
            "workspace_id": "workspace_dashpro",
            "goal": (
                "Verification after Marco (backend): run scoped verify commands — "
                "`npm test -- tests/unit/services/staffVisibility.test.ts` "
                "[from run run_demo]"
            ),
        }
        jobs = [
            {
                "job_id": "agent-job-verify",
                "run_id": "run_verify",
                "status": "completed",
                "exit_code": 0,
                "command": "npm test -- tests/unit/services/staffVisibility.test.ts",
            }
        ]
        with patch(
            "app.workspace_agents.verification_execution.verification_terminal_jobs_for_run",
            return_value=jobs,
        ), patch(
            "app.runs.service.get_run",
            return_value={"history_ref": "hist-verify"},
        ), patch(
            "app.persistence.run_store.list_history",
            return_value=[],
        ):
            payload = build_verification_acceptance_evaluation(
                run_id="run_verify",
                task=task,
            )
        self.assertTrue(payload["passed"])
        self.assertIn("acceptance=pass", payload["summary"])

    def test_verification_acceptance_rejects_missing_exit_code(self) -> None:
        from unittest.mock import patch

        task = {
            "workspace_id": "workspace_dashpro",
            "goal": "Verification after Marco (backend): `npm test` [from run run_demo]",
        }
        jobs = [{"status": "completed", "exit_code": None, "command": "npm test"}]
        with patch(
            "app.workspace_agents.verification_execution.verification_terminal_jobs_for_run",
            return_value=jobs,
        ), patch(
            "app.runs.service.get_run",
            return_value={"history_ref": "hist-verify"},
        ), patch(
            "app.persistence.run_store.list_history",
            return_value=[],
        ):
            payload = build_verification_acceptance_evaluation(
                run_id="run_verify",
                task=task,
            )
        self.assertFalse(payload["passed"])
        self.assertIn("incomplete", payload["summary"])


if __name__ == "__main__":
    unittest.main()
