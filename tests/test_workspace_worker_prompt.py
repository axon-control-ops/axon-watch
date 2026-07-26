from __future__ import annotations

import unittest

import sys
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import EmployeeConfig  # noqa: E402
from app.workspace_agents.worker_prompt import (  # noqa: E402
    OUT_OF_SCOPE_GUARD_MARKER,
    build_continuous_worker_prompt,
    parse_out_of_scope_guard,
)


class WorkspaceWorkerPromptTests(unittest.TestCase):
    def test_build_continuous_worker_prompt_includes_role_and_workspace(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Shell Craft",
                    role="frontend",
                    owns="Vue shell and IDE polish",
                    schedule="continuous",
                ),
            )
        self.assertIn("workspace_axon_watch", prompt)
        self.assertIn("frontend", prompt)
        self.assertIn("Shell Craft", prompt)
        self.assertIn("Vue shell and IDE polish", prompt)
        self.assertIn("busy-poll", prompt)

    def test_backend_prompt_includes_ci_review_clause(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Control Plane",
                    role="backend",
                    owns="APIs, runs, approvals, and persistence",
                    schedule="continuous",
                ),
            )
        self.assertIn("verify:contracts", prompt)
        self.assertIn("Confidence: X/10", prompt)
        self.assertNotIn("bare FAILED", prompt.replace("never a bare FAILED", ""))

    def test_prompt_includes_prior_failure_detail_for_retry(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.latest_role_run_outcome",
            return_value={
                "run_id": "run_failed_backend",
                "outcome": "failed",
                "detail": "verify:contracts — test_run_outcome.py: assertion failed",
                "phase": "failed",
                "terminal": "1",
            },
        ), patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Control Plane",
                    role="backend",
                    owns="APIs, runs, approvals, and persistence",
                    schedule="continuous",
                ),
            )
        self.assertIn("Prior shift failed (run run_failed_backend)", prompt)
        self.assertIn("assertion failed", prompt)
        self.assertIn("Prefer fixing or clearing that failure", prompt)

    def test_prompt_omits_prior_failure_when_last_shift_completed(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.latest_role_run_outcome",
            return_value={
                "run_id": "run_ok_backend",
                "outcome": "completed",
                "detail": "Shipped scheduler controls with receipts.",
                "phase": "completed",
                "terminal": "1",
            },
        ), patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Control Plane",
                    role="backend",
                    owns="APIs, runs, approvals, and persistence",
                    schedule="continuous",
                ),
            )
        self.assertNotIn("Prior shift failed", prompt)

    def test_prompt_omits_prior_failure_for_control_plane_restart(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.latest_role_run_outcome",
            return_value=None,
        ), patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Rowan",
                    role="watcher",
                    owns="signals, connectors, and runtime health",
                    schedule="always_on",
                ),
            )
        self.assertNotIn("Prior shift failed", prompt)
        self.assertNotIn("control-plane restart", prompt)

    def test_lead_prompt_includes_authoritative_team_roster(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.latest_role_run_outcome",
            return_value=None,
        ), patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value=(
                "Company team roster (authoritative — do not search the repo for this):\n"
                "- Dana (Lead / lead)[LEAD] — owns: priorities\n"
                "- Priya (Frontend / frontend) — owns: payments UI\n"
                "Do NOT Glob, Grep, or Read the filesystem to discover teammates"
            ),
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
                    "task_id": "task-lead-1",
                    "goal": "Coordinate July fee reconciliation handoffs",
                },
            )
        self.assertIn("You are Dana, the lead employee", prompt)
        self.assertIn("treat the company team roster block as authoritative", prompt)
        self.assertIn("do not Glob/Grep/Read the tree to discover staffing", prompt)
        self.assertIn("Priya (Frontend / frontend)", prompt)
        self.assertIn("Do NOT Glob, Grep, or Read", prompt)

    def test_prompt_includes_scope_guard_for_leased_tasks(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_young_eagles",
                employee=EmployeeConfig(
                    name="Lila",
                    role="frontend",
                    owns="letters, printable packs, and parent-facing layouts",
                    schedule="always_on",
                ),
                task={
                    "task_id": "task-readme",
                    "goal": "Update `young_eagles_day_care/README.md` so the docs stay focused on the internal operations workspace.",
                    "acceptance_criteria": "README only; no unrelated posters, event graphics, or marketing copy",
                },
            )
        self.assertIn("Hard scope anchors", prompt)
        self.assertIn("young_eagles_day_care/README.md", prompt)
        self.assertIn("Do not drift into neighboring files", prompt)
        self.assertIn(OUT_OF_SCOPE_GUARD_MARKER, prompt)

    def test_parse_out_of_scope_guard_returns_detail(self) -> None:
        detail = parse_out_of_scope_guard(
            "OUT_OF_SCOPE_GUARD: outputs/posts/young-eagles-pj-party.jpg is not required for this leased task"
        )
        self.assertEqual(
            "outputs/posts/young-eagles-pj-party.jpg is not required for this leased task",
            detail,
        )
        self.assertIsNone(parse_out_of_scope_guard("Everything stayed on task."))

    def test_prompt_surfaces_explicit_allowed_paths(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Rowan",
                    role="watcher",
                    owns="Fast Gate and file-size hygiene",
                    schedule="continuous",
                ),
                task={
                    "task_id": "task-patrol-1",
                    "goal": "File-size patrol: lower stale ratchet",
                    "acceptance_criteria": "manifest only",
                    "allowed_paths": ["scripts/guardrails/hotspot_budgets.json"],
                },
            )
        self.assertIn("Explicit allowed write paths", prompt)
        self.assertIn("scripts/guardrails/hotspot_budgets.json", prompt)
        self.assertNotIn("Hard scope anchors", prompt)


if __name__ == "__main__":
    unittest.main()
