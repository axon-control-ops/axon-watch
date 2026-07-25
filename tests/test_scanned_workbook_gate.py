from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.chat.reply_verification import verify_lane_b_reply  # noqa: E402
from app.chat.scanned_workbook_gate import (  # noqa: E402
    ASSIGNMENT_DOCUMENT_QUALITY_RULE,
    assignment_workbook_policy_appendix,
    scan_scanned_workbook_completion_risks,
    scanned_workbook_context,
)
from app.cli_runtime.router import _build_prompt  # noqa: E402

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "scanned_workbook"
    / "unit_13855_set_b_only.json"
)


class ScannedWorkbookGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_flags_missing_set_a_inventory(self) -> None:
        warnings = scan_scanned_workbook_completion_risks(
            str(self.fixture["agent_reply"]),
            user_prompt=str(self.fixture["user_prompt"]),
            context_block=str(self.fixture["context_snippet"]),
        )
        self.assertTrue(warnings)
        self.assertTrue(
            any("Learning Unit only" in item for item in warnings),
            warnings,
        )
        self.assertTrue(
            any("full-page" in item for item in warnings),
            warnings,
        )

    def test_full_inventory_reply_passes_gate(self) -> None:
        reply = (
            "Status: COMPLETE\n\n"
            "Inventory (scanned workbook):\n"
            "- Set A / Question/Activity — pages 7–18 (A1–A13)\n"
            "- Set B / Learning Unit 1 — pages 23–38 (1–12)\n\n"
            "## Set A\nA1. Observation methods...\n"
            "## Learning Unit 1\n1. As a practitioner...\n"
        )
        warnings = scan_scanned_workbook_completion_risks(
            reply,
            user_prompt=str(self.fixture["user_prompt"]),
        )
        self.assertEqual(warnings, [])

    def test_non_workbook_task_ignored(self) -> None:
        warnings = scan_scanned_workbook_completion_risks(
            "Status: COMPLETE — README updated.",
            user_prompt="Fix the README typo in this repo.",
        )
        self.assertEqual(warnings, [])

    def test_policy_appendix_injected_for_scanned_workbook(self) -> None:
        policy = assignment_workbook_policy_appendix(
            str(self.fixture["user_prompt"]),
            str(self.fixture["context_snippet"]),
        )
        self.assertIn(ASSIGNMENT_DOCUMENT_QUALITY_RULE, policy)
        self.assertIn("full-page question/activity inventory", policy)

    def test_reference_assignment_pdf_gets_full_quality_rule_without_scan_signal(self) -> None:
        policy = assignment_workbook_policy_appendix(
            "Create the same assignment as /tmp/Annatjie_Unit_13855.pdf for Mildred.",
        )
        self.assertIn("operator-named reference file as authoritative", policy)
        self.assertIn("Inspect every image after", policy)
        self.assertIn("exact page count", policy)
        self.assertNotIn("Scanned workbook policy", policy)

    def test_printable_evidence_pack_gets_full_quality_rule(self) -> None:
        policy = assignment_workbook_policy_appendix(
            "Render the final printable evidence pack and verify it.",
        )
        self.assertIn(ASSIGNMENT_DOCUMENT_QUALITY_RULE, policy)

    def test_every_composer_mode_includes_assignment_quality_rule(self) -> None:
        for mode, tier in (
            ("agent", "executing"),
            ("ask", "consultative"),
            ("plan", "consultative"),
            ("debug", "executing"),
        ):
            with self.subTest(mode=mode):
                prompt = _build_prompt(
                    composer_mode=mode,
                    user_prompt=str(self.fixture["user_prompt"]),
                    context_block=str(self.fixture["context_snippet"]),
                    execution_tier=tier,
                )
                self.assertIn(ASSIGNMENT_DOCUMENT_QUALITY_RULE, prompt)
                self.assertIn("Scanned workbook policy", prompt)

    def test_verify_lane_b_reply_appends_notice_for_fixture(self) -> None:
        verified, warnings = verify_lane_b_reply(
            str(self.fixture["agent_reply"]),
            execution_tier="executing",
            user_prompt=str(self.fixture["user_prompt"]),
            context_block=str(self.fixture["context_snippet"]),
        )
        self.assertTrue(warnings)
        self.assertIn("Verification notice", verified)
        self.assertTrue(scanned_workbook_context(str(self.fixture["user_prompt"])))


if __name__ == "__main__":
    unittest.main()
