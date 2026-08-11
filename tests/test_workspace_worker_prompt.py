from __future__ import annotations

import unittest

import sys
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from tests.support.control_plane_db import isolate_control_plane_db  # noqa: E402

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
        self.assertIn("one missing optional documentation/playbook path", prompt)
        self.assertIn("Avoid a combined multi-file read", prompt)

    def test_prompt_includes_cross_role_receipts_for_specialist_handoffs(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ), patch(
            "app.workspace_agents.worker_prompt._workspace_continuity_clause",
            return_value=(
                "Recent cross-role continuity packet (receipt summaries, not proof that your task is done):\n"
                "- backend completed (run-marco-1) — parent assignment query fixed\n"
                "Inspect the actual implementation and rerun the acceptance checks; report any contradiction to Lead."
            ),
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_dashpro",
                employee=EmployeeConfig(
                    name="Priya",
                    role="frontend",
                    owns="DashPro mobile UI",
                    schedule="on_demand",
                ),
                task={"task_id": "task-priya-1", "goal": "Align the parent carousel."},
            )
        self.assertIn("Recent cross-role continuity packet", prompt)
        self.assertIn("parent assignment query fixed", prompt)
        self.assertIn("not proof that your task is done", prompt)

    def test_dashpro_ship_prompt_does_not_block_on_disposable_git(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_dashpro",
                employee=EmployeeConfig(
                    name="Soren",
                    role="integrations",
                    owns="DashPro OTA and release guardrails",
                    schedule="continuous",
                ),
                task={
                    "task_id": "task-ota",
                    "goal": "Publish the verified DashPro fix to canary using npm run ota:canary.",
                },
            )
        self.assertIn("Disposable worker checkouts may intentionally lack usable `.git` metadata", prompt)
        self.assertIn("real workspace by `--workspace`", prompt)
        self.assertIn("retry the helper with `--no-stream`", prompt)
        self.assertIn("own branch, dirty-tree, and auth guards", prompt)

    def test_prompt_teaches_safe_worker_delivery(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_axon_watch",
                employee=EmployeeConfig(
                    name="Reed",
                    role="backend",
                    owns="Control-plane APIs and persistence",
                    schedule="continuous",
                ),
            )
        self.assertIn("Delivery discipline", prompt)
        self.assertIn("Do not run `git add -A`, commit, push, merge, force-push", prompt)
        self.assertIn("stages only your verified changed paths", prompt)
        self.assertIn("outside the leased task", prompt)

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

    def test_integrations_prompt_includes_full_access_tools_clause(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_young_eagles_day_care",
                employee=EmployeeConfig(
                    name="Sol",
                    role="integrations",
                    owns="Document export hooks and EduDash linkage",
                    schedule="continuous",
                ),
            )
        self.assertIn("Full Access for project Shell", prompt)
        self.assertIn("verification scripts", prompt)
        self.assertNotIn("spin on Task/MCP workarounds", prompt.replace(
            "Do not spin on Task/MCP workarounds for basic ls/node/npm checks.",
            "",
        ))
        self.assertIn("Do not spin on Task/MCP workarounds", prompt)

    def test_dashpro_prompt_locks_self_hosted_ci(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_dashpro",
                employee=EmployeeConfig(
                    name="Soren",
                    role="integrations",
                    owns="DashPro GitHub Actions on self-hosted runners",
                    schedule="continuous",
                ),
            )
        self.assertIn("runs-on: self-hosted", prompt)
        self.assertIn("ubuntu-latest", prompt)
        self.assertIn("billing-blocked", prompt)

    def test_dashpro_prompt_teaches_supabase_vault_self_heal(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_dashpro",
                employee=EmployeeConfig(
                    name="Marco",
                    role="backend",
                    owns="DashPro Supabase and assignment data",
                    schedule="continuous",
                ),
                task={
                    "task_id": "task-migration-audit",
                    "goal": "Audit Supabase migration history without deploying.",
                },
            )
        self.assertIn("Supabase CLI self-heal", prompt)
        self.assertIn("SUPABASE_ACCESS_TOKEN", prompt)
        self.assertIn("never ask for pasted tokens in chat", prompt)
        self.assertIn("Do not run `supabase db push` without separate operator deployment approval", prompt)

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

    def test_leased_prompt_uses_current_task_packet_not_prior_failure(self) -> None:
        with patch(
            "app.workspace_agents.worker_prompt.latest_role_run_outcome",
            return_value={
                "run_id": "run_stale_frontend",
                "outcome": "failed",
                "detail": "continue after server restart",
                "phase": "failed",
                "terminal": "1",
            },
        ), patch(
            "app.workspace_agents.worker_prompt.build_team_roster_context",
            return_value="",
        ):
            prompt = build_continuous_worker_prompt(
                workspace_id="workspace_dashpro",
                employee=EmployeeConfig(
                    name="Priya",
                    role="frontend",
                    owns="DashPro UI",
                    schedule="continuous",
                ),
                task={
                    "task_id": "task-current-student-ui",
                    "goal": "Redesign the Student Management header UI.",
                    "acceptance_criteria": "Changed files and targeted validation required.",
                    "allowed_paths": ["app", "components"],
                },
            )
        self.assertIn("Current task packet", prompt)
        self.assertIn("task-current-student-ui", prompt)
        self.assertIn("Redesign the Student Management header UI", prompt)
        self.assertIn("ignore stale thread context", prompt)
        self.assertNotIn("Prior shift failed", prompt)
        self.assertNotIn("continue after server restart", prompt)

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
        self.assertIn("You are Dana. Your role is lead", prompt)
        self.assertIn("treat the company team roster block as authoritative", prompt)
        self.assertIn("do not Glob/Grep/Read the tree to discover staffing", prompt)
        self.assertIn("Priya (Frontend / frontend)", prompt)
        self.assertIn("Do NOT Glob, Grep, or Read", prompt)

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
