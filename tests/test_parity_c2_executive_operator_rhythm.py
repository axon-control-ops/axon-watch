"""P-C2 executive operator rhythm parity tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.operator_briefing_rhythm import EXECUTIVE_RHYTHM_KEYS  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run  # noqa: E402


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityC2ExecutiveOperatorRhythmTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _briefing_with_probe(self) -> dict[str, object]:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            response = self.client.get("/api/briefing")
        self.assertEqual(200, response.status_code)
        return response.json()

    def test_default_verify_wiring_includes_parity_c2_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_c2_executive_operator_rhythm", verify_script)

    def test_briefing_executive_rhythm_has_full_contract(self) -> None:
        create_run(
            workspace_id="workspace_smoke",
            mode="agent",
            summary="P-C2 rhythm parity run",
            requires_approval=True,
        )
        payload = self._briefing_with_probe()
        rhythm = payload["executive_rhythm"]

        self.assertEqual(set(EXECUTIVE_RHYTHM_KEYS), set(rhythm))
        self.assertEqual(payload["notice"], rhythm["notice"])
        self.assertEqual(payload["advise"], rhythm["advise"])
        for key in EXECUTIVE_RHYTHM_KEYS:
            self.assertTrue(str(rhythm[key]).strip(), msg=f"{key} must be non-empty")

    def test_rhythm_decide_execute_verify_derived_from_canonical_state(self) -> None:
        create_run(
            workspace_id="workspace_smoke",
            mode="agent",
            summary="Approval-bound rhythm run",
            requires_approval=True,
        )
        payload = self._briefing_with_probe()
        rhythm = payload["executive_rhythm"]

        self.assertIn("approve or reject", rhythm["decide"].lower())
        self.assertIn("approve", rhythm["execute"].lower())
        self.assertIn("approval boundary", rhythm["verify"].lower())
        self.assertIn("pending approval", rhythm["report"].lower())
        self.assertEqual(payload["next_safe_actions"][0]["kind"], "approve_run")
        self.assertIn("approval", payload["notice"].lower())
        self.assertIn("Approve", payload["advise"])

    def test_contract_fixture_passes_rhythm_checker(self) -> None:
        from scripts.verify.check_executive_operator_rhythm import validate_executive_rhythm

        fixture = REPO_ROOT / "packages/shared-types/fixtures/operator-briefing.example.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        result = validate_executive_rhythm(payload)
        self.assertEqual("pass", result.status)


if __name__ == "__main__":
    unittest.main()
