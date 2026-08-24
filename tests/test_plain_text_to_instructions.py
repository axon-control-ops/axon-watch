from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.plain_text_to_instructions import (  # noqa: E402
    build_instructions_markdown_from_source,
    compose_instructions_markdown,
    extract_instructions_markdown,
    instructions_block_git_actions,
    instructions_markdown_is_complete,
    prompt_requests_git_actions,
)
from app.specialist_roles import SpecialistContext, role_profile  # noqa: E402
from app.routes.chat import composer_instructions_generate  # noqa: E402
from app.routes.schemas import GenerateInstructionsRequest  # noqa: E402


def specialist_context(role: str, name: str | None = None) -> SpecialistContext:
    profile = role_profile(role)
    return SpecialistContext(
        role=role,
        agent_name=name or profile.display_name,
        workspace_id="workspace_young_eagles_day_care",
        workspace_label="Young Eagles Day Care",
        employee_id=f"employee_{role}",
        allowed_paths=(f"{role}/",),
        read_scope=(".",),
        write_scope=(f"{role}/",),
        composer_mode="agent",
        requested_delivery_mode=profile.preferred_delivery_mode,
        delivery_capabilities=("workspace_read", "workspace_write"),
        role_label=profile.display_name,
        owns=f"{profile.display_name} lane",
        verified=True,
    )


class PlainTextToInstructionsTests(unittest.TestCase):
    def test_negated_commit_mention_is_not_git_intent(self) -> None:
        prompt = (
            "Look at what Dashpro workspace said about the CI work and plan how the "
            "Agents we have built would handle that. I never said anything about committing."
        )
        self.assertFalse(prompt_requests_git_actions(prompt))

    def test_instructions_out_of_scope_blocks_git(self) -> None:
        prompt = """# Instructions

## Goal
Plan CI handling.

## Out of scope
- Committing, amending, or inventing commit chores

## Steps
1. Read the triage note.
"""
        self.assertTrue(instructions_block_git_actions(prompt))
        self.assertFalse(prompt_requests_git_actions(prompt))

    def test_explicit_commit_still_detected(self) -> None:
        self.assertTrue(prompt_requests_git_actions("commit these changes"))
        self.assertTrue(prompt_requests_git_actions("please commit and push"))

    def test_extract_instructions_from_fenced_markdown(self) -> None:
        raw = """Here is the brief:

```markdown
# Instructions

## Goal
Fix GIF rendering.

## Source request
Make GIFs look like WhatsApp.
```"""
        extracted = extract_instructions_markdown(raw)
        self.assertIsNotNone(extracted)
        self.assertTrue(extracted.startswith("# Instructions"))
        self.assertIn("Fix GIF rendering.", extracted or "")

    def test_extract_instructions_after_preamble(self) -> None:
        raw = "Sure — converted below.\n\n# Instructions\n\n## Goal\nShip OTA safely.\n\n## In scope\n- OTA\n\n## Out of scope\n- Commit\n\n## Steps\n1. One\n2. Two\n3. Three\n\n## Constraints\n- Safe\n\n## Source request\nShip OTA safely.\n"
        extracted = extract_instructions_markdown(raw)
        self.assertTrue(extracted is not None and extracted.startswith("# Instructions"))

    def test_build_instructions_from_long_source(self) -> None:
        source = (
            "Connect the Young Eagles workspace as Teacher-X in DashPro. "
            "The team needs to know layout, features, screens, homework, assignments, grading, "
            "reports, and official languages for preschool and K-12."
        )
        built = build_instructions_markdown_from_source(source)
        self.assertTrue(instructions_markdown_is_complete(built))
        self.assertIn("Teacher-X", built)
        self.assertIn("## Source request", built)

    def test_frontend_fallback_is_specialist_aware(self) -> None:
        source = "Fix the mobile sign in screen layout and verify it on a phone viewport."
        context = specialist_context("frontend", "Lila")
        built = build_instructions_markdown_from_source(source, context)
        self.assertTrue(instructions_markdown_is_complete(built, context))
        self.assertIn("## Assigned specialist", built)
        self.assertIn("- Role: Frontend", built)
        self.assertIn("- Agent: Lila", built)
        self.assertIn("responsive", built.lower())
        self.assertIn("accessibility", built.lower())
        self.assertIn("Backend receives API", built)

    def test_integrations_fallback_includes_secret_and_contract_evidence(self) -> None:
        source = "Connect the payments webhook and diagnose retry failures."
        context = specialist_context("integrations", "Quinn")
        built = compose_instructions_markdown(source, None, context)
        self.assertTrue(instructions_markdown_is_complete(built, context))
        self.assertIn("- Role: Integrations", built)
        self.assertIn("Secret-redaction", built)
        self.assertIn("Authentication-path checks", built)
        self.assertIn("Webhook or callback checks", built)
        self.assertIn("Backend receives APIs", built)
        self.assertIn("Frontend receives screens", built)

    def test_lead_fallback_is_coordination_not_default_implementation(self) -> None:
        source = "Make the dashboard sync register marks from Teacher-X."
        context = specialist_context("lead", "Imani")
        built = compose_instructions_markdown(source, None, context)
        self.assertTrue(instructions_markdown_is_complete(built, context))
        self.assertIn("- Role: Lead", built)
        self.assertIn("Decompose implementation work", built)
        self.assertIn("owned specialist tasks", built)
        self.assertIn("Do not become the default implementation agent", built)
        self.assertNotIn("Lead owned work: Vue components", built)

    def test_backend_fallback_routes_ui_work_to_frontend(self) -> None:
        source = "Add the register API, persist attendance, and expose errors for the UI."
        context = specialist_context("backend", "Cole")
        built = compose_instructions_markdown(source, None, context)
        self.assertTrue(instructions_markdown_is_complete(built, context))
        self.assertIn("- Role: Backend", built)
        self.assertIn("Server routes", built)
        self.assertIn("Authorization checks", built)
        self.assertIn("Migration-safety checks", built)
        self.assertIn("Frontend receives presentation", built)

    def test_watcher_fallback_defaults_to_read_only_verification(self) -> None:
        source = "Check whether the register sync actually works and report failures."
        context = specialist_context("watcher", "Rowan")
        built = compose_instructions_markdown(source, None, context)
        self.assertTrue(instructions_markdown_is_complete(built, context))
        self.assertIn("- Role: Watcher", built)
        self.assertIn("read-only verification task", built)
        self.assertIn("Required write scope: none by default", built)
        self.assertIn("Do not edit product files", built)
        self.assertIn("Expected-versus-actual comparison", built)

    def test_same_source_produces_distinct_specialist_outputs(self) -> None:
        source = "Fix the mobile control-plane command flow and verify evidence."
        outputs = {
            role: compose_instructions_markdown(source, None, specialist_context(role))
            for role in ("integrations", "lead", "backend", "frontend", "watcher")
        }
        self.assertEqual(len(set(outputs.values())), 5)
        for role, output in outputs.items():
            context = specialist_context(role)
            self.assertTrue(instructions_markdown_is_complete(output, context))
            self.assertIn(f"- Role: {role_profile(role).display_name}", output)
            self.assertIn("## Role mandate", output)
            self.assertIn("## Ownership boundaries", output)
            self.assertIn("## Validation", output)
            self.assertIn("## Handoff", output)

        self.assertIn("Secret-redaction", outputs["integrations"])
        self.assertIn("Decompose implementation work", outputs["lead"])
        self.assertIn("Server routes", outputs["backend"])
        self.assertIn("Vue components", outputs["frontend"])
        self.assertIn("read-only verification task", outputs["watcher"])

    def test_model_role_mismatch_falls_back_to_selected_specialist(self) -> None:
        source = "Fix the dashboard UI."
        context = specialist_context("frontend", "Lila")
        model = (
            "# Instructions\n\n"
            "## Assigned specialist\n- Role: Backend\n- Agent: Cole\n- Workspace: Young Eagles Day Care\n- Delivery mode: Scoped workspace-delivery task\n\n"
            "## Role mandate\nBackend owns server work.\n\n"
            "## Ownership boundaries\n### Owned by this specialist\n- Server work\n\n### Requires handoff\n- UI to Frontend\n\n"
            "## Goal\nFix the dashboard UI.\n\n"
            "## Context\nThe operator requested a UI fix.\n\n"
            "## Delivery mode\n- Scoped workspace-delivery task\n\n"
            "## In scope\n- UI\n\n"
            "## Out of scope\n- Commit\n\n"
            "## Steps\n1. One\n2. Two\n3. Three\n4. Four\n\n"
            "## Acceptance criteria\n- UI fixed\n\n"
            "## Validation\n- Browser smoke\n\n"
            "## Constraints\n- Do not claim unverified work\n"
        )
        composed = compose_instructions_markdown(source, model, context)
        self.assertIn("- Role: Frontend", composed)
        self.assertNotIn("- Role: Backend", composed)

    def test_general_fallback_labels_missing_specialist(self) -> None:
        built = compose_instructions_markdown("Fix the thing.", None)
        self.assertTrue(instructions_markdown_is_complete(built))
        self.assertIn("No specialist role was supplied. Confirm ownership before implementation.", built)

    def test_route_fallback_carries_selected_specialist_context(self) -> None:
        body = GenerateInstructionsRequest(
            workspace_id="workspace_young_eagles_day_care",
            content="Fix the visible mobile layout.",
            specialist_context={
                "role": "frontend",
                "agent_name": "Lila",
                "employee_id": "missing-lila",
                "composer_mode": "agent",
            },
        )
        with patch(
            "app.routes.chat.generate_lane_b_result",
            return_value={
                "dispatched": False,
                "reason": "model timeout",
                "runtime_id": "",
                "runtime_label": "",
            },
        ):
            response = composer_instructions_generate(body)
        content = str(response["content"])
        self.assertTrue(bool(response["fallback"]))
        self.assertEqual(response["specialist_role"], "frontend")
        self.assertIn("- Role: Frontend", content)
        self.assertIn("- Agent: Lila", content)

    def test_route_rejects_unknown_specialist_role(self) -> None:
        body = GenerateInstructionsRequest(
            workspace_id="workspace_young_eagles_day_care",
            content="Fix the visible mobile layout.",
            specialist_context={"role": "wizard"},
        )
        with self.assertRaises(Exception) as raised:
            composer_instructions_generate(body)
        self.assertIn("unsupported specialist role", str(raised.exception))

    def test_compose_instructions_fills_missing_model_sections(self) -> None:
        source = "Fix GIF rendering on mobile before OTA."
        model = "# Instructions\n\n## Source request\nFix GIF rendering on mobile before OTA.\n"
        composed = compose_instructions_markdown(source, model)
        self.assertTrue(instructions_markdown_is_complete(composed))
        self.assertIn("## Steps", composed)

    def test_model_output_complete_without_source_request(self) -> None:
        model = (
            "# Instructions\n\n"
            "## Goal\nFix GIF rendering on mobile before OTA.\n\n"
            "## Context\nConvert the request into a delivery-ready task.\n\n"
            "## Delivery mode\n- Run as scoped workspace delivery\n\n"
            "## In scope\n- Mobile GIF renderer\n\n"
            "## Out of scope\n- Committing or releasing unless explicitly requested\n\n"
            "## Steps\n1. One\n2. Two\n3. Three\n4. Four\n\n"
            "## Acceptance criteria\n- GIF rendering is visibly fixed\n\n"
            "## Validation\n- Run the relevant mobile smoke check\n\n"
            "## Constraints\n- Follow only the steps listed above\n"
        )
        self.assertTrue(instructions_markdown_is_complete(model))
        composed = compose_instructions_markdown("Fix GIF rendering on mobile before OTA.", model)
        self.assertNotIn("## Source request", composed)

    def test_compose_preserves_model_assumptions(self) -> None:
        source = "Fix GIF rendering on mobile before OTA."
        model = (
            "# Instructions\n\n"
            "## Goal\nFix GIF rendering on mobile before OTA.\n\n"
            "## Context\nConvert the request into a delivery-ready task.\n\n"
            "## Delivery mode\n- Run as scoped workspace delivery\n\n"
            "## In scope\n- Mobile GIF renderer\n\n"
            "## Out of scope\n- Committing or releasing unless explicitly requested\n\n"
            "## Steps\n1. One\n2. Two\n3. Three\n4. Four\n\n"
            "## Acceptance criteria\n- GIF rendering is visibly fixed\n\n"
            "## Validation\n- Run the relevant mobile smoke check\n\n"
            "## Constraints\n- Follow only the steps listed above\n\n"
            "## Assumptions\n- Assuming the Android build path since none was named — confirm before merging\n"
        )
        composed = compose_instructions_markdown(source, model)
        self.assertIn("## Assumptions", composed)
        self.assertIn("Android build path", composed)

    def test_fallback_omits_assumptions_when_model_silent(self) -> None:
        source = "Fix GIF rendering on mobile before OTA."
        composed = compose_instructions_markdown(source, None)
        self.assertNotIn("## Assumptions", composed)

    def test_fallback_requires_workspace_delivery_for_agent_file_edits(self) -> None:
        source = (
            "Lila fix the Young Eagles sign in screen in command-centre/assets/app.js "
            "so the username and password fields show."
        )
        composed = compose_instructions_markdown(source, None)
        self.assertTrue(instructions_markdown_is_complete(composed))
        self.assertIn("## Context", composed)
        self.assertIn("## Delivery mode", composed)
        self.assertIn("workspace-delivery task", composed)
        self.assertIn("command-centre/assets/app.js", composed)
        self.assertIn("changed files", composed)
        self.assertIn("## Acceptance criteria", composed)
        self.assertIn("## Validation", composed)

    def test_commit_sha_reference_is_not_git_intent(self) -> None:
        self.assertFalse(
            prompt_requests_git_actions(
                "Real DashPro fix commit: 2c0870708ddaa54550fb602c7fd3026c46e7ebb3"
            )
        )
        self.assertFalse(
            prompt_requests_git_actions(
                "Publish the verified commit 2c0870708ddaa54550fb602c7fd3026c46e7ebb3 to canary"
            )
        )


if __name__ == "__main__":
    unittest.main()
